import os
import sys
from pathlib import Path

import pytest

from bolt_core.runtime.process_supervisor import ManagedProcessSpec, RuntimeProcessSupervisor
from bolt_core.runtime.workspace_projection import WorkspaceProjection

PAYLOAD_PYTHON = Path(__file__).parents[1] / "src" / "bolt_core" / "runtime-releases" / "hermes" / "0.18.2" / "bin" / "python.exe"


def _spec(tmp_path: Path, args: object = None) -> ManagedProcessSpec:
    source_workspace = tmp_path / "source-workspace"
    source_workspace.mkdir()
    session_root = tmp_path / "runtimes" / "sessions" / "session_12345678"
    projection = WorkspaceProjection.create(source_workspace, session_root)
    return ManagedProcessSpec(
        runtime_id="hermes",
        implementation_version="1.2.3",
        args=args if args is not None else [sys.executable, "-c", "import time; time.sleep(60)"],
        managed_runtime_root=tmp_path / "runtimes",
        session_root=session_root,
        working_directory=projection.workspace_root,
        environment={},
        workspace_projection=projection,
    )


def test_process_spec_rejects_shell_command_string(tmp_path):
    with pytest.raises(ValueError, match="args"):
        _spec(tmp_path, "hermes acp --unsafe")


def test_process_spec_rejects_environment_overrides_for_sensitive_names(tmp_path):
    with pytest.raises(ValueError, match="sensitive"):
        ManagedProcessSpec(
            runtime_id="hermes",
            implementation_version="1.2.3",
            args=[sys.executable, "-c", "pass"],
            managed_runtime_root=tmp_path / "runtimes",
            session_root=tmp_path / "sessions" / "session_12345678",
            working_directory=tmp_path / "sessions" / "session_12345678" / "workspace",
            environment={"OPENAI_API_KEY": "forbidden"},
        )


def test_process_spec_rejects_unapproved_environment_overrides(tmp_path):
    with pytest.raises(ValueError, match="not permitted"):
        ManagedProcessSpec(
            runtime_id="hermes",
            implementation_version="1.2.3",
            args=[sys.executable, "-c", "pass"],
            managed_runtime_root=tmp_path / "runtimes",
            session_root=tmp_path / "sessions" / "session_12345678",
            working_directory=tmp_path / "sessions" / "session_12345678" / "workspace",
            environment={"PYTHONPATH": "injected"},
        )


def test_process_spec_allows_only_control_plane_runtime_token(tmp_path):
    spec = ManagedProcessSpec(
        runtime_id="hermes",
        implementation_version="1.2.3",
        args=[sys.executable, "-c", "pass"],
        managed_runtime_root=tmp_path / "runtimes",
        session_root=tmp_path / "sessions" / "session_12345678",
        working_directory=tmp_path / "sessions" / "session_12345678" / "workspace",
        environment={"BOLT_RUNTIME_TOKEN": "issued-by-control-plane"},
    )

    assert spec.environment["BOLT_RUNTIME_TOKEN"] == "issued-by-control-plane"


def test_supervisor_starts_with_isolated_directories_and_clean_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "parent-secret")
    monkeypatch.setenv("BOLT_AGENT_CORE_TOKEN", "core-secret")
    output = tmp_path / "runtimes" / "sessions" / "session_12345678" / "workspace" / "environment.txt"
    program = (
        "import os, pathlib, sys; "
        "pathlib.Path(sys.argv[1]).write_text("
        "'|'.join((os.environ.get('OPENAI_API_KEY', ''), "
        "os.environ.get('BOLT_AGENT_CORE_TOKEN', ''), os.environ['HERMES_HOME'], "
        "os.environ['HOME'], os.environ['TEMP'])))"
    )
    spec = _spec(tmp_path, [str(PAYLOAD_PYTHON), "-B", "-c", program, str(output)])
    supervisor = RuntimeProcessSupervisor()

    process = supervisor.start(spec)
    assert process.wait(timeout=5) == 0

    values = output.read_text().split("|")
    assert values[:2] == ["", ""]
    assert values[2:4] == [
        str(spec.session_root / "hermes-home"),
        str(spec.session_root / "home"),
    ]
    assert Path(values[4]).resolve().is_relative_to((spec.session_root / "home").resolve())
    record = supervisor.record(process.pid)
    assert record.runtime_id == "hermes"
    assert record.implementation_version == "1.2.3"
    assert record.args == tuple(spec.args)
    assert record.exit_code == 0
    assert record.last_heartbeat is not None


def test_supervisor_rejects_unmanaged_working_directory(tmp_path):
    spec = _spec(tmp_path)
    unmanaged = Path(os.environ.get("TEMP", str(tmp_path))) / "outside-workspace"
    spec = ManagedProcessSpec(**{**spec.__dict__, "working_directory": unmanaged})

    with pytest.raises(ValueError, match="workspace_projection_required"):
        RuntimeProcessSupervisor().start(spec)


def test_supervisor_terminates_running_process_tree(tmp_path):
    spec = _spec(tmp_path)
    supervisor = RuntimeProcessSupervisor()
    process = supervisor.start(spec)

    supervisor.stop(process.pid, timeout=0.1)

    assert process.poll() is not None
    assert supervisor.record(process.pid).exit_code is not None
