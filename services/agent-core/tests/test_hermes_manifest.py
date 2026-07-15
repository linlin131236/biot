from hashlib import sha256
from pathlib import Path

import pytest

from bolt_core.runtime.hermes_installer import HermesInstaller
from bolt_core.runtime.hermes_manifest import HERMES_UPSTREAM_COMMIT, HermesManifest


def _manifest(executable: Path) -> HermesManifest:
    return HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="0.9",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
    )


def _staging(tmp_path: Path) -> tuple[Path, Path]:
    staging = tmp_path / "managed" / ".staging" / "0.24.0"
    executable = staging / "bin" / "hermes-acp.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"fixed-hermes-acp")
    return staging, executable


def test_hermes_manifest_is_fixed_to_audited_runtime_identity(tmp_path):
    _staging_dir, executable = _staging(tmp_path)
    manifest = _manifest(executable)

    assert manifest.runtime_id == "hermes"
    assert manifest.upstream_commit == HERMES_UPSTREAM_COMMIT
    assert manifest.source == "https://github.com/NousResearch/hermes-agent"
    assert manifest.license == "MIT"
    assert manifest.capabilities.supports("permissions") is True


@pytest.mark.parametrize("relative_path", ["../hermes-acp.exe", "C:/hermes-acp.exe", "C:hermes-acp.exe", "bin/../../hermes"])
def test_manifest_rejects_non_relative_executable_path(tmp_path, relative_path):
    _staging_dir, executable = _staging(tmp_path)

    with pytest.raises(ValueError, match="executable_relative_path"):
        HermesManifest(
            implementation_version="0.24.0",
            acp_protocol_version="0.9",
            executable_relative_path=relative_path,
            executable_sha256=sha256(executable.read_bytes()).hexdigest(),
        )


def test_manifest_rejects_hash_mismatch_and_path_outside_managed_root(tmp_path):
    staging, executable = _staging(tmp_path)
    manifest = _manifest(executable)
    executable.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="SHA-256"):
        manifest.verify_installation(tmp_path / "managed", staging)
    with pytest.raises(ValueError, match="managed runtime root"):
        manifest.verify_installation(tmp_path / "other", staging)


def test_manifest_rejects_symlinked_executable(tmp_path):
    staging, executable = _staging(tmp_path)
    target = tmp_path / "outside.exe"
    target.write_bytes(executable.read_bytes())
    executable.unlink()
    try:
        executable.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable on this Windows test host")
    manifest = HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="0.9",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(target.read_bytes()).hexdigest(),
    )

    with pytest.raises(ValueError, match="reparse"):
        manifest.verify_installation(tmp_path / "managed", staging)


def test_installer_validates_staging_then_atomically_activates_version(tmp_path):
    staging, executable = _staging(tmp_path)
    manifest = _manifest(executable)
    installer = HermesInstaller(tmp_path / "managed")

    installed = installer.install(manifest)

    assert installed == tmp_path / "managed" / "hermes" / "0.24.0"
    assert manifest.verify_installation(tmp_path / "managed", installed).read_bytes() == b"fixed-hermes-acp"
    assert installer.current_version("hermes") == "0.24.0"
    assert not staging.exists()


def test_installer_does_not_replace_running_or_existing_version(tmp_path):
    staging, executable = _staging(tmp_path)
    manifest = _manifest(executable)
    installer = HermesInstaller(tmp_path / "managed", running_versions=lambda: {"0.24.0"})

    with pytest.raises(ValueError, match="running"):
        installer.install(manifest)
    assert staging.exists()

    installer = HermesInstaller(tmp_path / "managed")
    installer.install(manifest)
    replacement, replacement_executable = _staging(tmp_path)
    replacement_executable.write_bytes(b"replacement")
    conflicting = HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="0.9",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(replacement_executable.read_bytes()).hexdigest(),
    )

    with pytest.raises(ValueError, match="already exists"):
        installer.install(conflicting)
    assert (tmp_path / "managed" / "hermes" / "0.24.0" / "bin" / "hermes-acp.exe").read_bytes() == b"fixed-hermes-acp"
