"""Staged, verified Hermes installation for Bolt-managed runtimes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from bolt_core.runtime.hermes_manifest import HermesManifest


class HermesInstaller:
    def __init__(
        self, managed_root: Path, running_versions: Callable[[], set[str]] | None = None
    ) -> None:
        self._root = managed_root
        self._running_versions = running_versions or (lambda: set())

    def install(self, manifest: HermesManifest) -> Path:
        """Install a legacy test fixture after executable verification only.

        Production callers must use ``install_release`` so every bundled file is
        validated against a catalog-owned inventory.
        """
        staging = self._staging_path(manifest)
        manifest.verify_installation(self._root, staging)
        return self._activate_installation(manifest, staging)

    def install_release(self, release) -> Path:
        """Atomically activate a catalog-owned release after full-tree validation."""
        manifest = release.manifest
        staging = self._staging_path(manifest)
        manifest.verify_installation(self._root, staging, require_complete_tree=True)
        return self._activate_installation(manifest, staging)

    def _activate_installation(self, manifest: HermesManifest, staging: Path) -> Path:
        version = self._version_path(manifest)
        if manifest.implementation_version in self._running_versions():
            raise ValueError("cannot replace a running Hermes version")
        if version.exists():
            raise ValueError("Hermes version already exists")
        version.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, version)
        self._activate(manifest.implementation_version)
        return version

    def current_version(self, runtime_id: str) -> str | None:
        if runtime_id != "hermes":
            raise ValueError("runtime_id must be hermes")
        marker = self._root / "hermes" / "current"
        return marker.read_text(encoding="ascii") if marker.is_file() else None

    def _staging_path(self, manifest: HermesManifest) -> Path:
        return self._root / ".staging" / manifest.implementation_version

    def _version_path(self, manifest: HermesManifest) -> Path:
        return self._root / "hermes" / manifest.implementation_version

    def _activate(self, version: str) -> None:
        marker = self._root / "hermes" / "current"
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(version, encoding="ascii")
        os.replace(temporary, marker)
