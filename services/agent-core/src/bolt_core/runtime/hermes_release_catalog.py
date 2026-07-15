"""Read-only catalog of Bolt-managed Hermes runtime releases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bolt_core.runtime.hermes_manifest import HermesArtifactFile, HermesManifest
from bolt_core.runtime.hermes_release_inventory import HERMES_RELEASE_FILES


class HermesReleaseUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class HermesRelease:
    manifest: HermesManifest
    artifact_relative_path: str
    executable_args: tuple[str, ...]

    def __post_init__(self) -> None:
        artifact = Path(self.artifact_relative_path)
        if (
            not isinstance(self.artifact_relative_path, str)
            or not self.artifact_relative_path
            or artifact.is_absolute()
            or bool(artifact.drive)
            or ".." in artifact.parts
        ):
            raise ValueError("artifact_relative_path must be a safe relative path")
        if not isinstance(self.executable_args, tuple) or any(
            not isinstance(argument, str) or not argument for argument in self.executable_args
        ):
            raise ValueError("executable_args must be a fixed argument tuple")
        if not self.manifest.has_complete_inventory:
            raise ValueError("managed Hermes releases require a complete file inventory")


class HermesReleaseCatalog:
    """Expose only releases compiled into the Bolt Agent Core package."""

    def __init__(self, releases: Iterable[HermesRelease] = ()) -> None:
        items = tuple(releases)
        versions = [release.manifest.implementation_version for release in items]
        if len(versions) != len(set(versions)):
            raise ValueError("Hermes release versions must be unique")
        self._releases = {release.manifest.implementation_version: release for release in items}

    @classmethod
    def bundled(cls) -> "HermesReleaseCatalog":
        manifest = HermesManifest(
            implementation_version="0.18.2",
            acp_protocol_version="1",
            executable_relative_path="bin/hermes-acp.exe",
            executable_sha256=_file_hash("bin/hermes-acp.exe"),
            files=tuple(HermesArtifactFile(path, digest) for path, digest in HERMES_RELEASE_FILES),
        )
        return cls((HermesRelease(manifest, "hermes/0.18.2", ("-I", "-B", "-m", "acp_adapter.entry")),))

    def releases(self) -> tuple[HermesRelease, ...]:
        return tuple(self._releases[version] for version in sorted(self._releases))

    def release(self, version: str | None = None) -> HermesRelease:
        if version is None:
            if len(self._releases) != 1:
                raise HermesReleaseUnavailable("release_unavailable")
            return next(iter(self._releases.values()))
        try:
            return self._releases[version]
        except KeyError as error:
            raise HermesReleaseUnavailable("release_unavailable") from error

    def contains(self, version: str) -> bool:
        return version in self._releases


def _file_hash(relative_path: str) -> str:
    for path, digest in HERMES_RELEASE_FILES:
        if path == relative_path:
            return digest
    raise RuntimeError("bundled Hermes inventory does not include the ACP executable")
