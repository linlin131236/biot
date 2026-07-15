import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bolt_core.runtime.events import RuntimeEvent, RuntimeEventKind
from bolt_core.runtime.process_supervisor import ManagedProcessSpec, RuntimeProcessSupervisor

PAYLOAD_PYTHON = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases" / "hermes" / "0.18.2" / "bin" / "python.exe"
REPO_ROOT = Path(__file__).parents[3]


@pytest.fixture()
def managed_root(tmp_path):
    root = REPO_ROOT / ".review-tmp" / "runtime-process-tree" / tmp_path.name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object process tree control is required")
def test_job_object_binds_and_terminates_entire_child_tree(tmp_path, managed_root):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, managed_root / "sessions" / "session_12345678",
    )
    marker = projection.workspace_root / "child.pid"
    program = (
        "import pathlib, subprocess, sys, time; "
        "child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8'); "
        "time.sleep(60)"
    )
    spec = _secure_spec(managed_root, projection, [str(PAYLOAD_PYTHON), "-B", "-c", program, str(marker)])
    supervisor = RuntimeProcessSupervisor()

    process = supervisor.start(spec)
    assert supervisor.record(process.pid).job_object_bound is True
    _wait_for_file(marker)
    child_pid = int(marker.read_text(encoding="utf-8"))
    supervisor.stop(process.pid, timeout=1)

    assert process.poll() is not None
    assert not _pid_is_running(child_pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object process tree control is required")
def test_shutdown_stops_all_bound_process_trees(tmp_path, managed_root):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    supervisor = RuntimeProcessSupervisor()
    child_pids = []
    for index in range(2):
        workspace = tmp_path / f"workspace-{index}"
        workspace.mkdir()
        projection = WorkspaceProjection.create(
            workspace, managed_root / "sessions" / f"session_1234567{index}",
        )
        marker = projection.workspace_root / "child.pid"
        program = (
            "import pathlib, subprocess, sys, time; "
            "child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
            "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8'); "
            "time.sleep(60)"
        )
        process = supervisor.start(_secure_spec(
            managed_root, projection, [str(PAYLOAD_PYTHON), "-B", "-c", program, str(marker)],
        ))
        _wait_for_file(marker)
        child_pids.append((process.pid, int(marker.read_text(encoding="utf-8"))))

    records = supervisor.stop_all(timeout=1)

    assert len(records) == 2
    assert all(not _pid_is_running(child_pid) for _parent, child_pid in child_pids)


def test_runtime_terminal_crash_preserves_in_flight_tool_and_approval(tmp_path):
    from bolt_core.persistence.database import Database
    from bolt_core.persistence.repositories import ControlPlaneRepository
    from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor, RuntimeSession
    from bolt_core.runtime.manager import RuntimeManager
    from bolt_core.runtime.registry import RuntimeRegistry
    from bolt_core.runtime_control_plane import RuntimeControlPlane

    class Runtime:
        descriptor = RuntimeDescriptor(
            "bolt-native", "0.1.0", "bolt-native", "v1", RuntimeCapabilities(),
        )

        def start(self, task_id, _request):
            return RuntimeSession("session_12345678", "bolt-native", task_id)

        def send(self, _session, _message):
            return None

        def resume(self, _session):
            return None

        def resolve_approval(self, _session, _approval_id, _approved):
            return None

        def cancel(self, _session):
            return None

        def close(self, _session):
            return None

    class Broker:
        def __init__(self):
            self.revoked = []

        def revoke_session(self, session):
            self.revoked.append(session)

        def stop(self):
            return None

    class Supervisor:
        def stop_all(self, _timeout):
            return ()

    repository = ControlPlaneRepository(Database.open(tmp_path / "data"))
    workspace_id = repository.save_workspace(tmp_path / "workspace")
    registry = RuntimeRegistry()
    runtime = Runtime()
    registry.register(runtime.descriptor, runtime)
    broker = Broker()
    manager = RuntimeManager(registry, on_session_closed=broker.revoke_session)
    control = RuntimeControlPlane(
        registry=registry, manager=manager, repository=repository, workspace_id=workspace_id,
        broker=broker, supervisor=Supervisor(), startable_runtime_ids=("bolt-native",),
    )
    started = control.start("bolt-native", "inspect", "read_only")
    session = RuntimeSession(started["session_id"], "bolt-native", repository.list_runtime_sessions(workspace_id)[0]["task_id"])
    control.ingest_event(session, _event(session, 2, RuntimeEventKind.TOOL_STARTED, {"tool_id": "tool_12345678"}))
    control.ingest_event(session, _event(
        session, 3, RuntimeEventKind.APPROVAL_REQUESTED,
        {"approval_id": "approval_12345678", "tool_id": "tool_12345678", "title": "Run command"},
    ))

    control.runtime_terminal(session, RuntimeEventKind.FAILED)

    record = repository.list_runtime_sessions(workspace_id)[0]
    events = repository.list_runtime_events(session.session_id)
    assert record["status"] == "failed"
    assert events[-1]["type"] == "failed"
    assert events[-1]["payload"] == {
        "error_code": "crashed",
        "abandoned_tool_ids": ["tool_12345678"],
        "abandoned_approval_ids": ["approval_12345678"],
    }


def _secure_spec(managed_root: Path, projection, args: list[str]) -> ManagedProcessSpec:
    return ManagedProcessSpec(
        runtime_id="hermes",
        implementation_version="1.2.3",
        args=args,
        managed_runtime_root=managed_root,
        session_root=projection.session_root,
        working_directory=projection.workspace_root,
        environment={},
        workspace_projection=projection,
    )


def _event(session, sequence, kind, payload):
    return RuntimeEvent(
        event_id=f"evt_{sequence}_12345678",
        task_id=session.task_id,
        runtime_id=session.runtime_id,
        session_id=session.session_id,
        sequence=sequence,
        timestamp=datetime.now(UTC),
        kind=kind,
        payload=payload,
    )


def _wait_for_file(path: Path) -> None:
    import time

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path}")


def _pid_is_running(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)
