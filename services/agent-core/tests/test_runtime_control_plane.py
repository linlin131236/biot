"""Runtime control-plane lifecycle and API tests."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from datetime import UTC, datetime

import httpx
import pytest

from bolt_core.app import create_app
from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor, RuntimeSession
from bolt_core.runtime.events import RuntimeEvent, RuntimeEventKind
from bolt_core.runtime.manager import RuntimeManager
from bolt_core.runtime.hermes_manifest import HermesArtifactFile, HermesManifest
from bolt_core.runtime.hermes_release_catalog import HermesRelease, HermesReleaseCatalog
from bolt_core.runtime.registry import RuntimeRegistry
from bolt_core.runtime_control_plane import RuntimeControlPlane


@dataclass
class FakeRuntime:
    descriptor: RuntimeDescriptor = RuntimeDescriptor(
        runtime_id="bolt-native", implementation_version="0.1.0",
        protocol_type="bolt-native", protocol_version="v1",
        capabilities=RuntimeCapabilities(messages=True, cancellation=True),
    )
    closed: list[RuntimeSession] | None = None
    sent: list[tuple[RuntimeSession, dict]] | None = None

    def __post_init__(self):
        self.closed = []
        self.sent = []

    def start(self, task_id, _request):
        return RuntimeSession("session_12345678", "bolt-native", task_id)

    def send(self, session, message):
        self.sent.append((session, message))

    def resume(self, _session):
        return None

    def resolve_approval(self, _session, _approval_id, _approved):
        return None

    def cancel(self, session):
        self.closed.append(session)

    def close(self, session):
        self.closed.append(session)


class Broker:
    def __init__(self):
        self.revoked = []
        self.issued = []
        self.stopped = False

    def issue(self, session, policy):
        self.issued.append((session, policy))
        return "core-issued-grant"

    def start(self):
        return None

    def revoke_session(self, session):
        self.revoked.append(session)

    def stop(self):
        self.stopped = True


class Supervisor:
    def __init__(self):
        self.stopped = False

    def stop_all(self, timeout):
        assert timeout == 1
        self.stopped = True
        return ()


def _control_plane(
    tmp_path, *, startable=(), managed_root=None, bundled_root=None, catalog=None, hermes_factory=None,
):
    from bolt_core.persistence.database import Database
    from bolt_core.persistence.repositories import ControlPlaneRepository

    repository = ControlPlaneRepository(Database.open(tmp_path / "data"))
    workspace_id = repository.save_workspace(tmp_path / "workspace")
    runtime = FakeRuntime()
    registry = RuntimeRegistry()
    registry.register(runtime.descriptor, runtime)
    broker = Broker()
    manager = RuntimeManager(registry, on_session_closed=broker.revoke_session)
    supervisor = Supervisor()
    return RuntimeControlPlane(
        registry=registry, manager=manager, repository=repository, workspace_id=workspace_id,
        broker=broker, supervisor=supervisor, startable_runtime_ids=startable,
        managed_runtime_root=managed_root, bundled_runtime_root=bundled_root,
        catalog=catalog, hermes_factory=hermes_factory,
    ), repository, runtime, broker, supervisor


def test_control_plane_persists_safe_runtime_state_and_revokes_before_close(tmp_path):
    control, repository, runtime, broker, _supervisor = _control_plane(
        tmp_path, startable=("bolt-native",),
    )

    started = control.start("bolt-native", "read code", "read_only")
    stopped = control.stop(started["session_id"])

    assert started["runtime_id"] == "bolt-native"
    assert started["status"] == "running"
    assert stopped == {"session_id": started["session_id"], "status": "stop_requested"}
    record = repository.list_runtime_sessions(control._workspace_id)[0]
    assert record["status"] == "cancelled"
    assert record["external_session_id"] == started["session_id"]
    assert broker.revoked == [RuntimeSession(started["session_id"], "bolt-native", record["task_id"])]
    assert runtime.closed


def test_control_plane_persists_adapter_terminal_failure_and_revokes_once(tmp_path):
    control, repository, _runtime, broker, _supervisor = _control_plane(
        tmp_path, startable=("bolt-native",),
    )
    started = control.start("bolt-native", "read code", "read_only")
    record = repository.list_runtime_sessions(control._workspace_id)[0]
    session = RuntimeSession(started["session_id"], "bolt-native", record["task_id"])

    control.runtime_terminal(session, RuntimeEventKind.FAILED)
    control.runtime_terminal(session, RuntimeEventKind.FAILED)

    updated = repository.list_runtime_sessions(control._workspace_id)[0]
    events = repository.list_runtime_events(session.session_id)
    assert updated["status"] == "failed"
    assert [event["type"] for event in events] == ["status", "failed"]
    assert events[-1]["payload"] == {
        "error_code": "crashed", "abandoned_tool_ids": [], "abandoned_approval_ids": [],
    }
    assert broker.revoked == [session]


def test_control_plane_persists_approval_request_as_waiting_for_human(tmp_path):
    control, repository, _runtime, _broker, _supervisor = _control_plane(
        tmp_path, startable=("bolt-native",),
    )
    started = control.start("bolt-native", "read code", "read_only")
    record = repository.list_runtime_sessions(control._workspace_id)[0]
    event = RuntimeEvent(
        event_id="evt_approval_12345678",
        task_id=record["task_id"],
        runtime_id="bolt-native",
        session_id=started["session_id"],
        sequence=2,
        timestamp=datetime.now(UTC),
        kind=RuntimeEventKind.APPROVAL_REQUESTED,
        payload={"approval_id": "approval_12345678", "tool_id": "tool_12345678", "title": "Review"},
    )

    control.ingest_event(RuntimeSession(started["session_id"], "bolt-native", record["task_id"]), event)

    updated = repository.list_runtime_sessions(control._workspace_id)[0]
    assert updated["status"] == "waiting_approval"


def test_control_plane_derives_model_grants_only_from_the_saved_default_profile(tmp_path):
    control, repository, _runtime, broker, _supervisor = _control_plane(tmp_path)
    repository.save_model_profile(
        "default", None, "fake", "http://localhost:11434/v1", "fake-model", 0.2,
        30.0, 8192, None, {},
    )
    session = RuntimeSession("session_12345678", "bolt-native", "task_12345678")
    control._broker = broker

    grant = control.model_grant(session)

    assert grant == "core-issued-grant"
    issued_session, policy = broker.issued[0]
    assert issued_session == session
    assert policy.model_profile_id == "default"
    assert policy.generation == 0
    assert policy.allowed_paths == ("/v1/chat/completions",)
    assert policy.budget == 32
    assert 0 < (policy.expires_at - datetime.now(UTC)).total_seconds() <= 300


def test_control_plane_derives_core_model_policy_without_exporting_a_proxy_grant(tmp_path):
    control, repository, _runtime, broker, _supervisor = _control_plane(tmp_path)
    repository.save_model_profile(
        "default", None, "fake", "http://localhost:11434/v1", "fake-model", 0.2,
        30.0, 8192, None, {},
    )
    session = RuntimeSession("session_12345678", "hermes", "task_12345678")
    control._broker = broker

    policy = control.model_policy(session)

    assert broker.issued == []
    assert policy.model_profile_id == "default"
    assert policy.generation == 0
    assert policy.context_window == 8192
    assert policy.allowed_paths == ("/v1/chat/completions",)
    assert policy.budget == 32


def test_control_plane_registers_only_a_verified_overlay_hermes_runtime(tmp_path):
    managed_root = tmp_path / "managed"
    installation = managed_root / "hermes" / "0.24.0"
    executable = installation / "bin" / "hermes-acp.exe"
    bridge = installation / "bin" / "Lib" / "site-packages" / "acp_adapter" / "bolt_model_client.py"
    executable.parent.mkdir(parents=True)
    bridge.parent.mkdir(parents=True)
    executable.write_bytes(b"entry")
    bridge.write_text("# managed bridge\n", encoding="utf-8")
    manifest = HermesManifest(
        implementation_version="0.24.0", acp_protocol_version="1",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
        files=(
            HermesArtifactFile("bin/hermes-acp.exe", sha256(executable.read_bytes()).hexdigest()),
            HermesArtifactFile(
                "bin/Lib/site-packages/acp_adapter/bolt_model_client.py",
                sha256(bridge.read_bytes()).hexdigest(),
            ),
        ),
    )
    release = HermesRelease(manifest, "hermes/0.24.0", ("--check",))
    registered = []

    class HermesRuntime:
        descriptor = RuntimeDescriptor(
            "hermes", "0.24.0", "acp", "v1", RuntimeCapabilities(messages=True),
        )

    control, _repository, _runtime, _broker, _supervisor = _control_plane(
        tmp_path, managed_root=managed_root, catalog=HermesReleaseCatalog((release,)),
        hermes_factory=lambda received: registered.append(received) or HermesRuntime(),
    )

    control.startup()

    assert registered == [release]
    assert control.runtime_status("hermes")["start_available"] is True


def test_control_plane_reports_hermes_as_not_installed_when_catalog_release_exists(tmp_path):
    managed_root = tmp_path / "managed"
    bundled_root = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases"
    control, _repository, _runtime, _broker, _supervisor = _control_plane(
        tmp_path, managed_root=managed_root, bundled_root=bundled_root,
    )

    status = control.runtime_status("hermes")

    assert status["state"] == "not_installed"
    assert status["implementation_version"] == "0.18.2"
    assert status["start_available"] is False
    assert status["blocked_reason"] == "not_installed"
    with pytest.raises(Exception, match="not_installed"):
        control.start("hermes", "inspect", "read_only")


def test_control_plane_installs_bundled_hermes_and_keeps_workspace_gate_closed(tmp_path):
    managed_root = tmp_path / "managed"
    bundled_root = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases"
    control, _repository, _runtime, _broker, _supervisor = _control_plane(
        tmp_path, managed_root=managed_root, bundled_root=bundled_root,
    )

    installed = control.install_hermes()
    status = control.runtime_status("hermes")

    assert installed == {
        "runtime_id": "hermes", "state": "verified", "implementation_version": "0.18.2",
    }
    assert status["state"] == "verified"
    assert status["start_available"] is False
    assert status["blocked_reason"] == "workspace_projection_required"
    with pytest.raises(Exception, match="workspace_projection_required"):
        control.start("hermes", "inspect", "read_only")


def test_control_plane_registers_verified_bundled_hermes_immediately_after_install(tmp_path):
    managed_root = tmp_path / "managed"
    bundled_root = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases"
    registered = []

    class HermesRuntime:
        descriptor = RuntimeDescriptor(
            "hermes", "0.18.2", "acp", "v1", RuntimeCapabilities(messages=True),
        )

    control, _repository, _runtime, _broker, _supervisor = _control_plane(
        tmp_path, managed_root=managed_root, bundled_root=bundled_root,
        hermes_factory=lambda release: registered.append(release) or HermesRuntime(),
    )

    installed = control.install_hermes()

    assert installed["state"] == "verified"
    assert registered == [HermesReleaseCatalog.bundled().release()]
    assert control.runtime_status("hermes")["start_available"] is True


def test_control_plane_sends_the_owned_task_after_session_persistence(tmp_path):
    control, repository, runtime, _broker, _supervisor = _control_plane(
        tmp_path, startable=("bolt-native",),
    )

    started = control.start("bolt-native", "inspect repository", "read_only")

    record = repository.list_runtime_sessions(control._workspace_id)[0]
    session = RuntimeSession(started["session_id"], "bolt-native", record["task_id"])
    assert runtime.sent == [(session, {"text": "inspect repository"})]


def test_control_plane_persists_completed_terminal_and_revokes_once(tmp_path):
    control, repository, _runtime, broker, _supervisor = _control_plane(
        tmp_path, startable=("bolt-native",),
    )
    started = control.start("bolt-native", "inspect", "read_only")
    record = repository.list_runtime_sessions(control._workspace_id)[0]
    session = RuntimeSession(started["session_id"], "bolt-native", record["task_id"])

    control.runtime_terminal(session, RuntimeEventKind.COMPLETED)

    updated = repository.list_runtime_sessions(control._workspace_id)[0]
    events = repository.list_runtime_events(session.session_id)
    assert updated["status"] == "completed"
    assert events[-1]["type"] == "completed"
    assert events[-1]["payload"] == {"summary": "Runtime completed"}
    assert broker.revoked == [session]


@pytest.mark.anyio
async def test_runtime_api_is_authenticated_sanitized_and_fails_closed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(
        project_dir=workspace, persistence_root=tmp_path / "data", local_api_token="token",
        require_local_api_token=True, desktop_production=True,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test",
    ) as client:
        unauthorized = await client.get("/runtime")
        listing = await client.get("/runtime", headers={"Authorization": "Bearer token"})
        invalid = await client.post(
            "/runtime/hermes/sessions", headers={"Authorization": "Bearer token"},
            json={"task": "hello", "mode": "read_only", "api_key": "secret"},
        )
        unavailable = await client.post(
            "/runtime/hermes/sessions", headers={"Authorization": "Bearer token"},
            json={"task": "hello", "mode": "read_only"},
        )

    assert unauthorized.status_code == 401
    hermes = next(item for item in listing.json()["runtimes"] if item["runtime_id"] == "hermes")
    assert hermes["state"] == "release_unavailable"
    assert "proxy_url" not in str(hermes)
    assert invalid.status_code == 422
    assert "secret" not in invalid.text
    assert unavailable.status_code == 409
    assert unavailable.json()["detail"] == "release_unavailable"


@pytest.mark.anyio
async def test_desktop_lifespan_uses_only_core_owned_model_authority(tmp_path):
    from bolt_core.model_gateway import FakeModelGateway
    from bolt_core.workspace_credential_gate import LockedWorkspace

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(
        project_dir=workspace,
        persistence_root=tmp_path / "data",
        local_api_token="token",
        require_local_api_token=True,
        desktop_production=True,
        model_gateway=FakeModelGateway(),
        locked_workspace_binding=LockedWorkspace("workspace_identity", 1),
        managed_runtime_root=tmp_path / "data" / "runtimes",
    )
    assert app.state.runtime_broker is None
    assert app.state.runtime_model_rpc is not None
    assert app.state.runtime_control_plane._hermes_factory is not None

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            response = await client.get("/runtime", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert app.state.runtime_control_plane.runtime_status("hermes")["state"] == "not_installed"
