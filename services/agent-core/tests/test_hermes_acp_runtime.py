import shutil
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from bolt_core.runtime.events import RuntimeEventKind
from bolt_core.runtime.hermes_acp import HermesAcpRuntime
from bolt_core.runtime.model_access import RuntimeModelPolicy, RuntimeProxyGrant
from bolt_core.runtime.hermes_manifest import HermesManifest
from bolt_core.runtime.process_supervisor import RuntimeProcessSupervisor

from runtime_security_support import (
    isolated_payload_installation,
    payload_python_sha256,
    shared_payload_installation,
)


FIXTURE = Path(__file__).parent / "fixtures" / "fake_acp_agent.py"


class RecordingSupervisor(RuntimeProcessSupervisor):
    def __init__(self):
        super().__init__()
        self.last_spec = None

    def start(self, spec):
        self.last_spec = spec
        return super().start(spec)


def _runtime(
    tmp_path, fixture=FIXTURE, model_grant_factory=None, supervisor=None,
    on_terminal=None, on_session_closed=None, model_policy_factory=None, model_rpc=None,
):
    managed, install = shared_payload_installation()
    executable = install / "bin" / "python.exe"
    manifest = HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="1",
        executable_relative_path="bin/python.exe",
        executable_sha256=payload_python_sha256(),
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return HermesAcpRuntime(
        manifest=manifest,
        installation=install,
        executable_args=["-I", "-B", "-c", fixture.read_text(encoding="utf-8")],
        supervisor=supervisor or RuntimeProcessSupervisor(),
        managed_runtime_root=managed,
        workspace=workspace,
        model_grant_factory=model_grant_factory,
        model_policy_factory=model_policy_factory,
        model_rpc=model_rpc,
        on_terminal=on_terminal,
        on_session_closed=on_session_closed,
    )


def test_hermes_acp_uses_core_model_bridge_without_loopback_credentials(tmp_path):
    class Rpc:
        def __init__(self):
            self.registered = []
            self.revoked = []

        def register(self, session, policy):
            self.registered.append((session, policy))

        def revoke(self, session):
            self.revoked.append(session)

    rpc = Rpc()
    policy = RuntimeModelPolicy(
        "profile_12345678", ("/v1/chat/completions",), 3,
        datetime.now(UTC) + timedelta(minutes=5), 4, 128_000,
    )
    supervisor = RecordingSupervisor()
    runtime = _runtime(
        tmp_path, supervisor=supervisor, model_rpc=rpc,
        model_policy_factory=lambda _session: policy,
    )

    session = runtime.start("task_12345678", {})

    config = (runtime._root / "sessions" / session.session_id / "hermes-home" / "config.yaml").read_text(encoding="utf-8")
    assert supervisor.last_spec.environment == {}
    assert "provider: bolt-managed" in config
    assert "provider: custom:bolt" not in config
    assert "BOLT_RUNTIME_TOKEN" not in config
    assert rpc.registered == [(session, policy)]
    runtime.close(session)
    assert rpc.revoked == [session]


def test_hermes_acp_rejects_legacy_proxy_grant_when_core_bridge_is_present(tmp_path):
    class Rpc:
        def register(self, _session, _policy):
            pass

        def revoke(self, _session):
            pass

    policy = RuntimeModelPolicy(
        "profile_12345678", ("/v1/chat/completions",), 3,
        datetime.now(UTC) + timedelta(minutes=5), 4, 128_000,
    )

    with pytest.raises(ValueError, match="legacy proxy grant"):
        _runtime(
            tmp_path, model_rpc=Rpc(), model_policy_factory=lambda _session: policy,
            model_grant_factory=lambda _session: RuntimeProxyGrant(
                "runtime-token", "http://127.0.0.1:43123/v1", 128_000,
            ),
        )


def test_hermes_acp_uses_only_core_issued_model_proxy_grant(tmp_path):
    grant = RuntimeProxyGrant("runtime-token", "http://127.0.0.1:43123/v1", 128_000)
    supervisor = RecordingSupervisor()
    runtime = _runtime(
        tmp_path, model_grant_factory=lambda _session: grant, supervisor=supervisor,
    )

    session = runtime.start("task_12345678", {})

    config = (
        runtime._root / "sessions" / session.session_id / "hermes-home" / "config.yaml"
    ).read_text(encoding="utf-8")
    assert supervisor.last_spec.environment == grant.environment
    assert "provider: custom:bolt" in config
    assert "api: http://127.0.0.1:43123/v1" in config
    assert "context_length: 128000" in config
    assert "X-Bolt-Runtime-Token: ${BOLT_RUNTIME_TOKEN}" in config
    assert "Authorization: ''" in config
    assert "runtime-token" not in config
    runtime.close(session)


def test_hermes_acp_uses_prompt_timeout_for_the_full_model_turn(tmp_path):
    runtime = _runtime(tmp_path)
    session = runtime.start("task_12345678", {})
    calls = []

    class PromptClient:
        def request(self, method, _params, timeout=5):
            calls.append((method, timeout))
            if method == "session/prompt":
                return {"stopReason": "end_turn"}
            return None

    runtime._states[session.session_id].client = PromptClient()
    runtime.send(session, {"text": "wait for the model"})

    runtime.drain_events(session)

    assert calls == [("session/prompt", 125)]
    runtime.close(session)


def test_hermes_acp_initializes_starts_prompts_and_cancels_over_stdio(tmp_path):
    runtime = _runtime(tmp_path)

    session = runtime.start("task_12345678", {"goal": "read only"})
    runtime.send(session, {"text": "inspect this repository"})
    events = runtime.drain_events(session)
    assert runtime.external_session_id(session) == "hermes-session"
    runtime.cancel(session)

    assert session.runtime_id == "hermes"
    assert runtime.descriptor.protocol_type == "acp"
    assert [event.kind.value for event in events] == ["message_delta", "usage_update", "completed"]
    assert events[0].payload["text"] == "hello from fake Hermes"
    assert events[1].payload == {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}


def test_hermes_acp_rejects_wrong_identity_protocol_or_capability(tmp_path):
    bad = tmp_path / "bad_agent.py"
    bad.write_text(
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " request=json.loads(line)\n"
        " print(json.dumps({'jsonrpc':'2.0','id':request.get('id'),'result':"
        "{'protocolVersion':99,'agentInfo':{'name':'impostor','version':'1'},'agentCapabilities':{}}}), flush=True)\n"
    )
    runtime = _runtime(tmp_path, bad)

    with pytest.raises(ValueError, match="initialize"):
        runtime.start("task_12345678", {})


def test_hermes_acp_rejects_tampered_managed_executable_before_start(tmp_path):
    runtime = _runtime(tmp_path)
    managed, installation = isolated_payload_installation(tmp_path.name)
    runtime._root = managed
    runtime._installation = installation
    executable = installation / "bin" / "python.exe"
    executable.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="SHA-256"):
        runtime.start("task_12345678", {})


def test_hermes_acp_refuses_resume_for_unknown_local_session(tmp_path):
    runtime = _runtime(tmp_path)
    session = runtime.start("task_12345678", {})
    runtime.close(session)

    with pytest.raises(ValueError, match="unknown Hermes session"):
        runtime.resume(session)


def test_hermes_acp_uses_isolated_home_with_external_extensions_disabled(tmp_path):
    runtime = _runtime(tmp_path)

    session = runtime.start("task_12345678", {})

    config = runtime._root / "sessions" / session.session_id / "hermes-home" / "config.yaml"
    assert config.read_text(encoding="utf-8") == "memory:\n  provider: ''\nplugins:\n  enabled: []\n"
    session_root = runtime._root / "sessions" / session.session_id
    runtime.close(session)
    assert not session_root.exists()


def test_hermes_acp_requires_explicit_approval_before_allowing_command(tmp_path):
    runtime = _runtime(tmp_path)
    session = runtime.start("task_12345678", {})

    runtime.send(session, {"text": "request permission"})
    events = runtime.drain_events(session, timeout=0.1)

    assert len(events) == 1
    assert events[0].kind.value == "approval_requested"
    assert events[0].payload["approval_id"] == "permission_123"
    runtime.resolve_approval(session, "permission_123", True)
    events = runtime.drain_events(session)
    assert any(event.payload.get("text") == "permission allow_once" for event in events)


def test_hermes_acp_rejects_permission_without_explicit_allow_once(tmp_path):
    runtime = _runtime(tmp_path)
    session = runtime.start("task_12345678", {})

    runtime.send(session, {"text": "request permission"})
    runtime.drain_events(session, timeout=0.1)
    runtime.resolve_approval(session, "permission_123", False)

    events = runtime.drain_events(session)

    assert any(event.payload.get("text") == "permission denied" for event in events)


def test_hermes_acp_unknown_event_fails_closed(tmp_path):
    bad = tmp_path / "bad_event_agent.py"
    bad.write_text(
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " request=json.loads(line); method=request.get('method'); identifier=request.get('id')\n"
        " if method=='initialize': result={'protocolVersion':1,'agentInfo':{'name':'hermes-agent','version':'0.24.0'},'agentCapabilities':{'loadSession':True}}\n"
        " elif method=='session/new': result={'sessionId':'hermes-session'}\n"
        " elif method=='session/prompt':\n"
        "  print(json.dumps({'jsonrpc':'2.0','method':'session/update','params':{'sessionId':'hermes-session','update':{'sessionUpdate':'permission_bypassed'}}}), flush=True); result={'stopReason':'end_turn'}\n"
        " else: result=None\n"
        " print(json.dumps({'jsonrpc':'2.0','id':identifier,'result':result}), flush=True)\n"
    )
    runtime = _runtime(tmp_path, bad)
    session = runtime.start("task_12345678", {})

    runtime.send(session, {"text": "test"})
    with pytest.raises(ValueError, match="unsupported ACP"):
        runtime.drain_events(session)


def test_hermes_acp_reports_an_unexpected_child_exit_once(tmp_path):
    agent = tmp_path / "exit_agent.py"
    agent.write_text(
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " request=json.loads(line); method=request.get('method'); identifier=request.get('id')\n"
        " if method=='initialize': result={'protocolVersion':1,'agentInfo':{'name':'hermes-agent','version':'0.24.0'},'agentCapabilities':{'loadSession':True}}\n"
        " elif method=='session/new': result={'sessionId':'hermes-session'}\n"
        " elif method=='session/prompt': sys.exit(7)\n"
        " else: result=None\n"
        " print(json.dumps({'jsonrpc':'2.0','id':identifier,'result':result}), flush=True)\n"
    )
    terminal = []
    runtime = _runtime(
        tmp_path, agent,
        on_terminal=lambda session, kind: terminal.append((session, kind)),
    )
    session = runtime.start("task_12345678", {})

    runtime.send(session, {"text": "exit now"})

    with pytest.raises(ValueError, match="ACP transport"):
        runtime.drain_events(session, timeout=2)
    assert terminal == [(session, RuntimeEventKind.FAILED)]


def test_hermes_acp_accepts_a_cancelled_prompt_outcome(tmp_path):
    agent = tmp_path / "cancelled_agent.py"
    agent.write_text(
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " request=json.loads(line); method=request.get('method'); identifier=request.get('id')\n"
        " if method=='initialize': result={'protocolVersion':1,'agentInfo':{'name':'hermes-agent','version':'0.24.0'},'agentCapabilities':{'loadSession':True}}\n"
        " elif method=='session/new': result={'sessionId':'hermes-session'}\n"
        " elif method=='session/prompt': result={'stopReason':'cancelled'}\n"
        " else: result=None\n"
        " print(json.dumps({'jsonrpc':'2.0','id':identifier,'result':result}), flush=True)\n"
    )
    terminal = []
    runtime = _runtime(
        tmp_path, agent,
        on_terminal=lambda session, kind: terminal.append((session, kind)),
    )
    session = runtime.start("task_12345678", {})

    runtime.send(session, {"text": "cancel"})

    assert runtime.drain_events(session) == []
    assert terminal == [(session, RuntimeEventKind.CANCELLED)]


def test_hermes_acp_revokes_grant_when_process_start_fails(tmp_path):
    class FailingSupervisor(RuntimeProcessSupervisor):
        def start(self, _spec):
            raise OSError("cannot start")

    closed = []
    runtime = _runtime(
        tmp_path,
        model_grant_factory=lambda _session: RuntimeProxyGrant(
            "runtime-token", "http://127.0.0.1:43123/v1", 128_000,
        ),
        supervisor=FailingSupervisor(),
        on_session_closed=closed.append,
    )

    with pytest.raises(OSError, match="cannot start"):
        runtime.start("task_12345678", {})

    assert len(closed) == 1
    assert closed[0].runtime_id == "hermes"
