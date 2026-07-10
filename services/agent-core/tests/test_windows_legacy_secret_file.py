import os
from pathlib import Path
import subprocess

import pytest

from bolt_core.windows_legacy_secret_file import (
    LegacySecretFileError,
    WindowsLegacySecretFiles,
)


pytestmark = pytest.mark.windows


def _make_junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Windows junction unavailable: {result.stderr or result.stdout}")


def _write_legacy(workspace: Path, content: bytes = b"legacy-secret") -> Path:
    key = workspace / ".bolt" / "desktop-api-key"
    key.parent.mkdir(parents=True)
    key.write_bytes(content)
    return key


def test_reads_and_deletes_a_regular_legacy_file_by_verified_handle(tmp_path):
    workspace = tmp_path / "workspace"
    key = _write_legacy(workspace)
    files = WindowsLegacySecretFiles()

    reference = files.open_selected(workspace)

    assert reference is not None
    assert files.read_bounded(reference, 2561) == b"legacy-secret"
    files.delete_verified(reference)

    assert not key.exists()


def test_rejects_a_workspace_ancestor_junction_before_opening_secret(tmp_path):
    target = tmp_path / "real-workspace"
    _write_legacy(target)
    workspace = tmp_path / "workspace-junction"
    _make_junction(workspace, target)

    with pytest.raises(LegacySecretFileError, match="credential_migration_failed"):
        WindowsLegacySecretFiles().open_selected(workspace)


def test_rejects_a_bolt_junction_before_opening_secret(tmp_path):
    workspace = tmp_path / "workspace"
    target = tmp_path / "outside-bolt"
    target.mkdir()
    (target / "desktop-api-key").write_bytes(b"legacy-secret")
    workspace.mkdir()
    _make_junction(workspace / ".bolt", target)

    with pytest.raises(LegacySecretFileError, match="credential_migration_failed"):
        WindowsLegacySecretFiles().open_selected(workspace)


def test_refuses_to_delete_after_same_path_is_replaced(tmp_path):
    workspace = tmp_path / "workspace"
    key = _write_legacy(workspace)
    files = WindowsLegacySecretFiles()
    reference = files.open_selected(workspace)
    assert reference is not None

    os.unlink(key)
    key.write_bytes(b"replacement-secret")

    with pytest.raises(LegacySecretFileError, match="credential_migration_failed"):
        files.delete_verified(reference)
    assert key.read_bytes() == b"replacement-secret"
