from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hashlib import sha256
import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from urllib.request import Request, urlopen

import pytest

from bolt_core.model_proxy import ModelProxyServer, RuntimeModelProxy
from bolt_core.persistence.database import Database
from bolt_core.runtime.acp_stdio import AcpStdioClient
from bolt_core.runtime.hermes_acp import HermesAcpRuntime
from bolt_core.runtime.hermes_manifest import HermesArtifactFile, HermesManifest
from bolt_core.runtime.hermes_release_catalog import HermesReleaseCatalog
from bolt_core.runtime.model_access import RuntimeModelAccessBroker, RuntimeModelPolicy
from bolt_core.runtime.model_rpc import RuntimeModelRpc
from bolt_core.runtime.process_supervisor import RuntimeProcessSupervisor
from bolt_core.runtime_token_store import RuntimeTokenStore


class _LocalProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self.server.requests.append({"headers": dict(self.headers), "body": body})
        payload = {
            "id": "local-response",
            "object": "chat.completion",
            "model": "local-test",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "LOCAL_PROVIDER_OK"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format, *_args):
        return


@contextmanager
def _local_provider():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalProviderHandler)
    server.requests = []
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/chat/completions", server.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


class _LocalProviderGateway:
    def __init__(self, endpoint):
        self._endpoint = endpoint

    def complete(self, _profile_id, request):
        outbound = Request(
            self._endpoint,
            data=json.dumps(request["payload"]).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(outbound, timeout=5) as response:
            return json.loads(response.read())


class _RecordingProxy:
    def __init__(self, delegate):
        self._delegate = delegate
        self.key_paths = []
        self.errors = []

    def complete(self, request):
        self.key_paths = _key_paths(request.payload)
        try:
            return self._delegate.complete(request)
        except Exception as error:
            self.errors.append(type(error).__name__)
            raise


def _key_paths(value, prefix=()):
    if isinstance(value, dict):
        paths = [".".join((*prefix, str(key))) for key in value]
        return paths + [path for key, item in value.items() for path in _key_paths(item, (*prefix, str(key)))]
    if isinstance(value, list):
        return [path for item in value for path in _key_paths(item, prefix)]
    return []


def _real_hermes_runtime(tmp_path, model_policy_factory, model_rpc, on_session_closed=None):
    release = HermesReleaseCatalog.bundled().release()
    source = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases" / release.artifact_relative_path
    managed_root = tmp_path / "managed"
    installation = managed_root / "hermes" / release.manifest.implementation_version
    shutil.copytree(source, installation)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Local provider E2E\n", encoding="utf-8")
    return HermesAcpRuntime(
        manifest=release.manifest,
        installation=installation,
        executable_args=release.executable_args,
        supervisor=RuntimeProcessSupervisor(),
        managed_runtime_root=managed_root,
        workspace=workspace,
        model_policy_factory=model_policy_factory,
        model_rpc=model_rpc,
        on_session_closed=on_session_closed,
    )


def _leaked_paths(roots, forbidden_values):
    leaks = []
    encoded = [value.encode("utf-8") for value in forbidden_values]
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and any(value in path.read_bytes() for value in encoded):
                leaks.append(path)
    return leaks


def _capture_safe_stderr(monkeypatch, chunks):
    def capture(client):
        stream = client._process.stderr
        if stream is None:
            return
        while chunk := stream.readline():
            chunks.append(chunk)

    monkeypatch.setattr(AcpStdioClient, "_drain_stderr", capture)


def _safe_stderr_summary(chunks, forbidden_values):
    text = b"".join(chunks).decode("utf-8", errors="replace")
    for value in forbidden_values:
        text = text.replace(value, "<redacted>")
    blocked = ("token", "authorization", "api_key", "secret")
    return [line[:300] for line in text.splitlines() if not any(word in line.lower() for word in blocked)][-20:]


def _safe_event_summary(events, forbidden_values):
    summary = []
    blocked = ("token", "authorization", "api_key", "secret")
    for event in events:
        text = str(event.payload.get("text") or event.payload.get("summary") or "")
        for value in forbidden_values:
            text = text.replace(value, "<redacted>")
        if any(word in text.lower() for word in blocked):
            text = "<redacted>"
        summary.append({"kind": event.kind.value, "keys": sorted(event.payload), "text": text[:300]})
    return summary


def _drain_until_terminal(runtime, session, timeout=60):
    deadline = monotonic() + timeout
    events = []
    while monotonic() < deadline:
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        try:
            events.extend(runtime.drain_events(session, timeout=min(5, remaining)))
        except ValueError as error:
            if str(error) != "ACP prompt did not produce an event":
                raise
        if any(event.kind.value in {"completed", "failed", "cancelled"} for event in events):
            return events
    return events


class _RecordingCoreGateway:
    def __init__(self):
        self.requests = []

    def complete(self, profile_id, request):
        self.requests.append({"profile_id": profile_id, "request": request})
        return {
            "id": "core-owned-response",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "LOCAL_PROVIDER_OK"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }


class _BlockingCoreGateway(_RecordingCoreGateway):
    def __init__(self):
        super().__init__()
        self.entered = Event()
        self.release = Event()

    def complete(self, profile_id, request):
        self.entered.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("test Core gateway remained blocked")
        return super().complete(profile_id, request)


def _overlay_payload_from_environment():
    payload = os.environ.get("BOLT_HERMES_OVERLAY_PAYLOAD")
    inventory = os.environ.get("BOLT_HERMES_OVERLAY_INVENTORY")
    if not payload or not inventory:
        return None
    payload_path, inventory_path = Path(payload), Path(inventory)
    if not payload_path.is_dir() or not inventory_path.is_file():
        raise AssertionError("configured Hermes overlay evidence is missing")
    entries = runpy.run_path(str(inventory_path))["HERMES_RELEASE_FILES"]
    return payload_path, tuple(HermesArtifactFile(path, digest) for path, digest in entries)


def _managed_overlay_copy(tmp_path, payload):
    installation = tmp_path / "managed" / "hermes" / payload.name
    shutil.copytree(payload, installation)
    return installation


def test_bundled_hermes_acp_check_runs_from_a_catalog_verified_managed_install(tmp_path):
    release = HermesReleaseCatalog.bundled().release()
    source = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases" / release.artifact_relative_path
    managed_root = tmp_path / "managed"
    installation = managed_root / "hermes" / release.manifest.implementation_version
    assert not list(source.rglob("__pycache__"))
    shutil.copytree(source, installation)

    executable = release.manifest.verify_installation(
        managed_root, installation, require_complete_tree=True,
    )
    result = subprocess.run(
        [str(executable), *release.executable_args, "--check"],
        cwd=installation,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "Hermes ACP check OK"


def test_bundled_managed_hermes_uses_only_core_owned_model_authority(tmp_path, monkeypatch):
    provider_canary = "synthetic-provider-key-not-for-use"
    monkeypatch.setenv("OPENAI_API_KEY", provider_canary)
    user_data = tmp_path / "user-data"
    database = Database.open(user_data)
    stderr_chunks = []
    _capture_safe_stderr(monkeypatch, stderr_chunks)
    gateway = _RecordingCoreGateway()
    rpc = RuntimeModelRpc(RuntimeModelProxy(RuntimeTokenStore(lambda: datetime.now(UTC)), gateway))
    policy = RuntimeModelPolicy(
        "local-profile", ("/v1/chat/completions",), 4,
        datetime.now(UTC) + timedelta(minutes=2), 1, 128_000,
    )
    runtime = _real_hermes_runtime(tmp_path, lambda _session: policy, rpc)
    session = None
    try:
        try:
            session = runtime.start("task_real_hermes", {})
        except ValueError as error:
            raise AssertionError(
                f"real Hermes session/new failed: {_safe_stderr_summary(stderr_chunks, [provider_canary])}"
            ) from error
        runtime.send(session, {"text": "Reply exactly LOCAL_PROVIDER_OK without tools."})
        events = _drain_until_terminal(runtime, session, timeout=90)
        diagnostics = {
            "core_request_count": len(gateway.requests),
            "events": _safe_event_summary(events, [provider_canary]),
            "stderr": _safe_stderr_summary(stderr_chunks, [provider_canary]),
        }
        if not any(event.kind.value == "completed" for event in events):
            raise AssertionError(json.dumps(diagnostics, ensure_ascii=True))
        assert len(gateway.requests) >= 1
        assert gateway.requests[0]["profile_id"] == "local-profile"
        assert gateway.requests[0]["request"]["path"] == "/v1/chat/completions"
        assert provider_canary not in json.dumps(gateway.requests)

        session_root = runtime._root / "sessions" / session.session_id
        config = (session_root / "hermes-home" / "config.yaml").read_text(encoding="utf-8")
        assert "provider: bolt-managed" in config
        assert "Authorization" not in config
        assert "http://127.0.0.1" not in config
        database.create_backup("real-hermes-core-boundary")
        assert _leaked_paths([session_root, user_data], [provider_canary]) == []
    finally:
        if session is not None:
            runtime.close(session)


def test_built_overlay_uses_acp_for_core_owned_model_authority(tmp_path, monkeypatch):
    evidence = _overlay_payload_from_environment()
    if evidence is None:
        pytest.skip("set BOLT_HERMES_OVERLAY_PAYLOAD and BOLT_HERMES_OVERLAY_INVENTORY")
    payload, files = evidence
    installation = _managed_overlay_copy(tmp_path, payload)
    executable = installation / "bin" / "hermes-acp.exe"
    manifest = HermesManifest(
        implementation_version="0.18.2",
        acp_protocol_version="1",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
        files=files,
    )
    managed_root = installation.parent
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# ACP Core model test\n", encoding="utf-8")
    provider_canary = "synthetic-provider-key-not-for-use"
    monkeypatch.setenv("OPENAI_API_KEY", provider_canary)
    gateway = _RecordingCoreGateway()
    rpc = RuntimeModelRpc(RuntimeModelProxy(RuntimeTokenStore(lambda: datetime.now(UTC)), gateway))
    policy = RuntimeModelPolicy(
        "local-profile", ("/v1/chat/completions",), 4,
        datetime.now(UTC) + timedelta(minutes=2), 1, 128_000,
    )
    runtime = HermesAcpRuntime(
        manifest=manifest,
        installation=installation,
        executable_args=["-I", "-B", "-m", "acp_adapter.entry"],
        supervisor=RuntimeProcessSupervisor(),
        managed_runtime_root=managed_root,
        workspace=workspace,
        model_policy_factory=lambda _session: policy,
        model_rpc=rpc,
    )
    session = None
    try:
        session = runtime.start("task_overlay_e2e", {})
        runtime.send(session, {"text": "Reply exactly LOCAL_PROVIDER_OK without tools."})
        events = _drain_until_terminal(runtime, session, timeout=90)
        assert any(event.kind.value == "completed" for event in events)
        assert len(gateway.requests) >= 1
        assert gateway.requests[0]["profile_id"] == "local-profile"
        assert gateway.requests[0]["request"]["path"] == "/v1/chat/completions"
        assert provider_canary not in json.dumps(gateway.requests)
        session_root = runtime._root / "sessions" / session.session_id
        config = (session_root / "hermes-home" / "config.yaml").read_text(encoding="utf-8")
        assert "provider: bolt-managed" in config
        assert "Authorization" not in config
        assert "http://127.0.0.1" not in config
        assert _leaked_paths([session_root], [provider_canary]) == []
    finally:
        if session is not None:
            runtime.close(session)


def test_built_overlay_cancel_does_not_wait_for_a_blocked_core_model_request(tmp_path, monkeypatch):
    evidence = _overlay_payload_from_environment()
    if evidence is None:
        pytest.skip("set BOLT_HERMES_OVERLAY_PAYLOAD and BOLT_HERMES_OVERLAY_INVENTORY")
    payload, files = evidence
    installation = _managed_overlay_copy(tmp_path, payload)
    executable = installation / "bin" / "hermes-acp.exe"
    manifest = HermesManifest(
        implementation_version="0.18.2",
        acp_protocol_version="1",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
        files=files,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    stderr_chunks = []
    _capture_safe_stderr(monkeypatch, stderr_chunks)
    monkeypatch.setattr(
        RuntimeProcessSupervisor, "_requires_projection", staticmethod(lambda _spec: False),
    )
    monkeypatch.setattr(
        RuntimeProcessSupervisor, "_requires_windows_projection", staticmethod(lambda _spec: False),
    )
    gateway = _BlockingCoreGateway()
    rpc = RuntimeModelRpc(RuntimeModelProxy(RuntimeTokenStore(lambda: datetime.now(UTC)), gateway))
    policy = RuntimeModelPolicy(
        "local-profile", ("/v1/chat/completions",), 4,
        datetime.now(UTC) + timedelta(minutes=2), 1, 128_000,
    )
    runtime = HermesAcpRuntime(
        manifest=manifest,
        installation=installation,
        executable_args=["-I", "-B", "-m", "acp_adapter.entry"],
        supervisor=RuntimeProcessSupervisor(),
        managed_runtime_root=installation.parent,
        workspace=workspace,
        model_policy_factory=lambda _session: policy,
        model_rpc=rpc,
    )
    try:
        session = runtime.start("task_overlay_cancel", {})
    except ValueError as error:
        raise AssertionError(
            f"real Hermes session/new failed: {_safe_stderr_summary(stderr_chunks, [])}"
        ) from error
    cancelled = Event()
    cancellation_errors = []

    def cancel() -> None:
        try:
            runtime.cancel(session)
        except Exception as error:
            cancellation_errors.append(error)
        finally:
            cancelled.set()

    cancellation = Thread(target=cancel, daemon=True)
    try:
        runtime.send(session, {"text": "Wait for Core model completion."})
        assert gateway.entered.wait(timeout=20)
        cancellation.start()
        assert cancelled.wait(timeout=5)
        assert cancellation_errors == []
    finally:
        gateway.release.set()
        cancellation.join(timeout=10)
        if not cancelled.is_set():
            runtime.close(session)
