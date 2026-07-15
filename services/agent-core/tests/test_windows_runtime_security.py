from datetime import UTC, datetime, timedelta
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from bolt_core.model_proxy import RuntimeModelProxy
from bolt_core.model_proxy_server import ModelProxyServer
from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.process_supervisor import ManagedProcessSpec, RuntimeProcessSupervisor
from bolt_core.runtime.model_access import (
    RuntimeModelAccessBroker, RuntimeModelPolicy, RuntimeProxyGrant,
)
from bolt_core.runtime_token_store import RuntimeTokenStore

PAYLOAD_PYTHON = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases" / "hermes" / "0.18.2" / "bin" / "python.exe"
REPO_ROOT = Path(__file__).parents[3]


class _LoopbackGateway:
    def __init__(self):
        self.calls = 0

    def complete(self, _profile_id, _payload):
        self.calls += 1
        return {"choices": [{"message": {"content": "safe"}}]}


def _loopback_broker():
    gateway = _LoopbackGateway()
    tokens = RuntimeTokenStore(lambda: datetime.now(UTC))
    broker = RuntimeModelAccessBroker(tokens, ModelProxyServer(RuntimeModelProxy(tokens, gateway)))
    broker.start()
    session = RuntimeSession("session_12345678", "hermes", "task_12345678")
    policy = RuntimeModelPolicy(
        "profile_12345678", ("/v1/chat/completions",), 4,
        datetime.now(UTC) + timedelta(minutes=2), 1, 128_000,
    )
    return broker, broker.issue(session, policy), gateway


def _host_proxy_request(grant):
    request = Request(
        f"{grant.proxy_url}/chat/completions",
        data=json.dumps({"messages": [{"role": "user", "content": "host"}]}).encode(),
        method="POST",
        headers={"X-Bolt-Runtime-Token": grant.token, "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=3) as response:
        return json.loads(response.read())["choices"][0]["message"]["content"]


def _appcontainer_proxy_program():
    return (
        "import json, os, pathlib, sys, urllib.request\n"
        "url=os.environ['BOLT_MODEL_PROXY_URL'].rstrip('/') + '/chat/completions'\n"
        "body=json.dumps({'messages':[{'role':'user','content':'child'}]}).encode()\n"
        "request=urllib.request.Request(url,data=body,method='POST',headers="
        "{'X-Bolt-Runtime-Token':os.environ['BOLT_RUNTIME_TOKEN'],'Content-Type':'application/json'})\n"
        "try:\n"
        " with urllib.request.urlopen(request,timeout=3) as response:\n"
        "  result=json.loads(response.read())['choices'][0]['message']['content']\n"
        "except Exception as error:\n"
        " reason=getattr(error,'reason',error)\n"
        " result=':'.join((type(error).__name__,type(reason).__name__,"
        "str(getattr(reason,'winerror','')),str(getattr(reason,'errno',''))))\n"
        "pathlib.Path(sys.argv[1]).write_text(result,encoding='utf-8')\n"
    )


@pytest.fixture()
def managed_root(tmp_path):
    root = REPO_ROOT / ".review-tmp" / "runtime-security" / tmp_path.name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _session_root(managed_root: Path) -> Path:
    return managed_root / "sessions" / "session_12345678"


@pytest.mark.skipif(os.name != "nt", reason="Windows restricted token support is required")
def test_windows_runtime_refuses_start_without_restricted_token_capability(tmp_path, managed_root, monkeypatch):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection
    import bolt_core.runtime.windows_process as windows_process

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, _session_root(managed_root),
    )
    monkeypatch.setattr(windows_process, "restricted_token_available", lambda _session_id: False)
    spec = _secure_spec(managed_root, projection)

    with pytest.raises(ValueError, match="workspace_projection_required"):
        RuntimeProcessSupervisor().start(spec)


@pytest.mark.skipif(os.name != "nt", reason="Windows restricted token support is required")
def test_restricted_runtime_environment_does_not_inherit_parent_secrets(tmp_path, managed_root, monkeypatch):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    for name in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "BOLT_CORE_BEARER",
        "BOLT_AGENT_CORE_TOKEN", "PROVIDER_SECRET",
    ):
        monkeypatch.setenv(name, f"parent-{name.lower()}")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, _session_root(managed_root),
    )
    output = projection.workspace_root / "env.txt"
    program = (
        "import os, pathlib, sys; "
        "names=['OPENAI_API_KEY','ANTHROPIC_API_KEY','BOLT_CORE_BEARER',"
        "'BOLT_AGENT_CORE_TOKEN','PROVIDER_SECRET']; "
        "pathlib.Path(sys.argv[1]).write_text('|'.join(os.environ.get(n,'') for n in names), encoding='utf-8')"
    )
    spec = _secure_spec(managed_root, projection, args=[str(PAYLOAD_PYTHON), "-B", "-c", program, str(output)])

    process = RuntimeProcessSupervisor().start(spec)
    assert process.wait(timeout=5) == 0

    assert output.read_text(encoding="utf-8") == "||||"


@pytest.mark.skipif(os.name != "nt", reason="Windows restricted token support is required")
def test_runtime_gets_only_short_lived_loopback_grant_not_real_provider_authority(tmp_path, managed_root, monkeypatch):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    monkeypatch.setenv("OPENAI_API_KEY", "real-openai-secret")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, _session_root(managed_root),
    )
    grant = RuntimeProxyGrant(
        "short-lived-runtime-token", "http://127.0.0.1:43123/v1", 128_000,
    )
    output = projection.workspace_root / "authority.txt"
    program = (
        "import os, pathlib, sys; "
        "keys=['BOLT_MODEL_PROXY_URL','BOLT_RUNTIME_TOKEN','OPENAI_API_KEY',"
        "'ANTHROPIC_API_KEY','BOLT_AGENT_CORE_TOKEN','BOLT_CORE_BEARER']; "
        "values={k: os.environ.get(k, '') for k in keys}; "
        "pathlib.Path(sys.argv[1]).write_text('\\n'.join(k + '=' + values[k] for k in keys), encoding='utf-8')"
    )
    spec = _secure_spec(
        managed_root, projection, args=[str(PAYLOAD_PYTHON), "-B", "-c", program, str(output)],
        environment=grant.environment,
    )

    process = RuntimeProcessSupervisor().start(spec)
    assert process.wait(timeout=5) == 0
    text = output.read_text(encoding="utf-8")

    assert "BOLT_MODEL_PROXY_URL=http://127.0.0.1:43123/v1" in text
    assert "BOLT_RUNTIME_TOKEN=short-lived-runtime-token" in text
    assert "real-openai-secret" not in text
    assert "BOLT_AGENT_CORE_TOKEN=" in text
    assert "BOLT_CORE_BEARER=" in text


@pytest.mark.skipif(os.name != "nt", reason="Windows AppContainer loopback is required")
def test_appcontainer_cannot_reach_legacy_core_loopback_proxy(tmp_path, managed_root):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(workspace, _session_root(managed_root))
    broker, grant, gateway = _loopback_broker()
    output = projection.workspace_root / "proxy-result.txt"
    try:
        assert _host_proxy_request(grant) == "safe"
        spec = _secure_spec(
            managed_root, projection,
            args=[str(PAYLOAD_PYTHON), "-B", "-c", _appcontainer_proxy_program(), str(output)],
            environment=grant.environment,
        )
        process = RuntimeProcessSupervisor().start(spec)
        assert process.wait(timeout=10) == 0
        assert output.read_text(encoding="utf-8").startswith("URLError:")
        assert gateway.calls == 1
    finally:
        broker.stop()


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL enforcement is required")
def test_acl_failure_refuses_start_without_plain_user_fallback(tmp_path, managed_root, monkeypatch):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, _session_root(managed_root),
    )
    degraded = projection.with_acl_enforced(False)
    spec = _secure_spec(managed_root, degraded)

    with pytest.raises(ValueError, match="workspace_projection_required"):
        RuntimeProcessSupervisor().start(spec)


@pytest.mark.skipif(os.name != "nt", reason="Windows restricted token support is required")
def test_bolt_does_not_explicitly_pass_pid_or_executable_path_to_runtime(tmp_path, managed_root):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, _session_root(managed_root),
    )
    output = projection.workspace_root / "metadata.txt"
    program = (
        "import os, pathlib, sys; "
        "pathlib.Path(sys.argv[1]).write_text('\\n'.join(sorted(os.environ)), encoding='utf-8')"
    )
    spec = _secure_spec(managed_root, projection, args=[str(PAYLOAD_PYTHON), "-B", "-c", program, str(output)])

    process = RuntimeProcessSupervisor().start(spec)
    assert process.wait(timeout=5) == 0
    names = output.read_text(encoding="utf-8").splitlines()

    assert "BOLT_RUNTIME_PID" not in names
    assert "BOLT_RUNTIME_EXECUTABLE" not in names
    assert "BOLT_HERMES_EXECUTABLE" not in names


@pytest.mark.skipif(os.name != "nt", reason="Windows AppContainer ACL enforcement is required")
def test_runtime_cannot_read_or_write_outside_projection(tmp_path, managed_root):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    projection = WorkspaceProjection.create(workspace, _session_root(managed_root))
    output = projection.workspace_root / "outside-access.txt"
    program = (
        "import pathlib, sys; source=pathlib.Path(sys.argv[1]); result=[]; "
        "\ntry: source.read_text(encoding='utf-8'); result.append('read-allowed')"
        "\nexcept (OSError, PermissionError): result.append('read-denied')"
        "\ntry: source.write_text('changed', encoding='utf-8'); result.append('write-allowed')"
        "\nexcept (OSError, PermissionError): result.append('write-denied')"
        "\npathlib.Path(sys.argv[2]).write_text('|'.join(result), encoding='utf-8')"
    )
    spec = _secure_spec(
        managed_root, projection,
        args=[str(PAYLOAD_PYTHON), "-B", "-c", program, str(outside), str(output)],
    )

    process = RuntimeProcessSupervisor().start(spec)
    assert process.wait(timeout=5) == 0

    assert output.read_text(encoding="utf-8") == "read-denied|write-denied"
    assert outside.read_text(encoding="utf-8") == "secret"


@pytest.mark.skipif(os.name != "nt", reason="Windows AppContainer isolation is required")
def test_appcontainer_identity_is_unique_per_runtime_session():
    from bolt_core.runtime.windows_appcontainer import appcontainer_sid_string

    first = appcontainer_sid_string("session_12345678")
    second = appcontainer_sid_string("session_87654321")

    assert first != second


def _secure_spec(managed_root: Path, projection, *, args=None, environment=None) -> ManagedProcessSpec:
    return ManagedProcessSpec(
        runtime_id="hermes",
        implementation_version="1.2.3",
        args=args if args is not None else [str(PAYLOAD_PYTHON), "-B", "-c", "pass"],
        managed_runtime_root=managed_root,
        session_root=_session_root(managed_root),
        working_directory=projection.workspace_root,
        environment=environment or {},
        workspace_projection=projection,
    )
