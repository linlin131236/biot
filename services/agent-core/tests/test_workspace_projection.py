import os
import subprocess
import sys
from pathlib import Path

import pytest

from bolt_core.runtime.process_supervisor import ManagedProcessSpec, RuntimeProcessSupervisor
from bolt_core.runtime_control_plane import RuntimeControlPlane


def test_projection_rejects_unc_workspace(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    root = tmp_path / "managed" / "sessions" / "session_12345678"

    with pytest.raises(ValueError, match="workspace_projection_required"):
        WorkspaceProjection.create(Path(r"\\server\share\project"), root)


def test_projection_excludes_workspace_secrets(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("safe", encoding="utf-8")
    (workspace / ".env").write_text("OPENAI_API_KEY=secret", encoding="utf-8")
    (workspace / "private.pem").write_text("private", encoding="utf-8")
    ssh = workspace / ".ssh"
    ssh.mkdir()
    (ssh / "id_ed25519").write_text("private", encoding="utf-8")

    projection = WorkspaceProjection.create(
        workspace, tmp_path / "managed" / "sessions" / "session_12345678",
    )

    assert (projection.workspace_root / "README.md").is_file()
    assert not (projection.workspace_root / ".env").exists()
    assert not (projection.workspace_root / "private.pem").exists()
    assert not (projection.workspace_root / ".ssh").exists()


def test_projection_rejects_nested_workspace_reparse_points(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        (workspace / "linked").symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("host does not allow directory symlinks")

    with pytest.raises(ValueError, match="workspace_projection_required"):
        WorkspaceProjection.create(workspace, tmp_path / "managed" / "sessions" / "session_12345678")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior is required")
def test_projection_rejects_nested_workspace_junction(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    junction = workspace / "linked"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("host does not allow junction creation")

    with pytest.raises(ValueError, match="workspace_projection_required"):
        WorkspaceProjection.create(
            workspace, tmp_path / "managed" / "sessions" / "session_12345678",
        )


def test_projection_rejects_external_working_directory(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = WorkspaceProjection.create(
        workspace, tmp_path / "managed" / "sessions" / "session_12345678",
    )

    with pytest.raises(ValueError, match="workspace_projection_required"):
        projection.validate_runtime_cwd(tmp_path / "outside")


def test_projection_materializes_only_controlled_workspace_root(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("inside", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    projection = WorkspaceProjection.create(
        workspace, tmp_path / "managed" / "sessions" / "session_12345678",
    )

    assert projection.workspace_root.is_dir()
    assert (projection.workspace_root / "README.md").read_text(encoding="utf-8") == "inside"
    assert projection.contains(projection.workspace_root / "README.md") is True
    assert projection.contains(outside) is False


def test_projection_materializes_empty_git_discovery_boundary(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source_git = workspace / ".git"
    source_git.mkdir()
    (source_git / "config").write_text("must-not-copy", encoding="utf-8")

    projection = WorkspaceProjection.create(
        workspace, tmp_path / "managed" / "sessions" / "session_12345678",
    )

    boundary = projection.workspace_root / ".git"
    assert boundary.is_dir()
    assert list(boundary.iterdir()) == []


def test_supervisor_refuses_hermes_without_workspace_projection(tmp_path):
    spec = ManagedProcessSpec(
        runtime_id="hermes",
        implementation_version="1.2.3",
        args=[sys.executable, "-c", "pass"],
        managed_runtime_root=tmp_path / "managed",
        session_root=tmp_path / "managed" / "sessions" / "session_12345678",
        working_directory=tmp_path / "managed" / "sessions" / "session_12345678" / "workspace",
        environment={},
    )

    with pytest.raises(ValueError, match="workspace_projection_required"):
        RuntimeProcessSupervisor().start(spec)


def test_control_plane_reports_workspace_projection_required_when_projection_fails(tmp_path):
    from bolt_core.persistence.database import Database
    from bolt_core.persistence.repositories import ControlPlaneRepository
    from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor
    from bolt_core.runtime.manager import RuntimeManager
    from bolt_core.runtime.registry import RuntimeRegistry
    from bolt_core.runtime.workspace_projection import WorkspaceProjectionError

    class HermesRuntime:
        descriptor = RuntimeDescriptor(
            "hermes", "0.18.2", "acp", "v1", RuntimeCapabilities(cancellation=True),
        )

        def start(self, _task_id, _request):
            raise WorkspaceProjectionError("workspace_projection_required")

    class Broker:
        def stop(self):
            return None

    class Supervisor:
        def stop_all(self, _timeout):
            return ()

    repository = ControlPlaneRepository(Database.open(tmp_path / "data"))
    workspace_id = repository.save_workspace(tmp_path / "workspace")
    registry = RuntimeRegistry()
    runtime = HermesRuntime()
    registry.register(runtime.descriptor, runtime)
    control = RuntimeControlPlane(
        registry=registry,
        manager=RuntimeManager(registry),
        repository=repository,
        workspace_id=workspace_id,
        broker=Broker(),
        supervisor=Supervisor(),
        startable_runtime_ids=("hermes",),
    )

    with pytest.raises(Exception, match="workspace_projection_required"):
        control.start("hermes", "inspect", "read_only")


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL enforcement is required")
def test_windows_projection_acl_denies_projection_external_file(tmp_path):
    from bolt_core.runtime.workspace_projection import WorkspaceProjection

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    projection = WorkspaceProjection.create(
        workspace, tmp_path / "managed" / "sessions" / "session_12345678",
    )

    assert projection.acl_enforced is True
    assert projection.can_restricted_token_read(projection.workspace_root) is True
    assert projection.can_restricted_token_read(outside) is False
