"""Hermes release catalog and managed-installation boundary tests."""

from hashlib import sha256
from pathlib import Path

import pytest

from bolt_core.runtime.hermes_manifest import HermesArtifactFile, HermesManifest
from bolt_core.runtime.hermes_release_catalog import (
    HermesRelease,
    HermesReleaseCatalog,
    HermesReleaseUnavailable,
)


def _release(tmp_path: Path) -> HermesRelease:
    executable = tmp_path / "bin" / "hermes-acp.exe"
    support = tmp_path / "Lib" / "site.py"
    executable.parent.mkdir(parents=True)
    support.parent.mkdir(parents=True)
    executable.write_bytes(b"entry")
    support.write_bytes(b"support")
    manifest = HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="1",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
        files=(
            HermesArtifactFile("bin/hermes-acp.exe", sha256(executable.read_bytes()).hexdigest()),
            HermesArtifactFile("Lib/site.py", sha256(support.read_bytes()).hexdigest()),
        ),
    )
    return HermesRelease(manifest, "hermes/0.24.0", ("acp",))


def test_bundled_catalog_exposes_the_audited_headless_acp_release():
    catalog = HermesReleaseCatalog.bundled()

    release = catalog.release()

    assert catalog.releases() == (release,)
    assert release.manifest.implementation_version == "0.18.2"
    assert release.artifact_relative_path == "hermes/0.18.2"
    assert release.executable_args == ("-I", "-B", "-m", "acp_adapter.entry")
    inventory = {item.relative_path for item in release.manifest.files}
    assert "bin/hermes-acp.exe" in inventory
    assert "bin/Lib/site-packages/acp_adapter/bolt_model_client.py" in inventory
    assert "licenses/HERMES-AGENT-MIT.txt" in inventory
    assert "metadata/provenance.json" in inventory


def test_release_catalog_rejects_a_manifest_without_a_complete_inventory(tmp_path):
    executable = tmp_path / "bin" / "hermes-acp.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"entry")
    manifest = HermesManifest(
        implementation_version="0.24.0",
        acp_protocol_version="1",
        executable_relative_path="bin/hermes-acp.exe",
        executable_sha256=sha256(executable.read_bytes()).hexdigest(),
    )

    with pytest.raises(ValueError, match="complete file inventory"):
        HermesRelease(manifest, "hermes/0.24.0", ("acp",))


def test_manifest_complete_inventory_rejects_missing_extra_and_tampered_files(tmp_path):
    source = tmp_path / "source"
    release = _release(source)
    installation = tmp_path / "managed" / "hermes" / "0.24.0"
    for path in source.rglob("*"):
        if path.is_file():
            target = installation / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())

    assert release.manifest.verify_installation(
        tmp_path / "managed", installation, require_complete_tree=True
    ) == installation / "bin" / "hermes-acp.exe"

    (installation / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected file"):
        release.manifest.verify_installation(
            tmp_path / "managed", installation, require_complete_tree=True
        )


def test_catalog_only_accepts_one_fixed_release_for_default_selection(tmp_path):
    first = _release(tmp_path / "first")
    second = _release(tmp_path / "second")
    second = HermesRelease(
        HermesManifest(
            implementation_version="0.25.0",
            acp_protocol_version=second.manifest.acp_protocol_version,
            executable_relative_path=second.manifest.executable_relative_path,
            executable_sha256=second.manifest.executable_sha256,
            files=second.manifest.files,
        ),
        second.artifact_relative_path,
        second.executable_args,
    )
    catalog = HermesReleaseCatalog((first, second))

    with pytest.raises(HermesReleaseUnavailable, match="release_unavailable"):
        catalog.release()
    assert catalog.release("0.24.0") is first
