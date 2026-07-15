"""Fixed identity and artifact validation for Bolt's Hermes runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import re

from bolt_core.runtime.contracts import RuntimeCapabilities

HERMES_UPSTREAM_COMMIT = "291eae63b7d37129661082e23df35804c5e89365"
_HERMES_SOURCE = "https://github.com/NousResearch/hermes-agent"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class HermesArtifactFile:
    relative_path: str
    sha256: str

    def __post_init__(self) -> None:
        if not _is_safe_artifact_path(self.relative_path):
            raise ValueError("artifact file path must be a safe relative path")
        if not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256):
            raise ValueError("artifact file SHA-256 must be SHA-256")


@dataclass(frozen=True)
class HermesManifest:
    implementation_version: str
    acp_protocol_version: str
    executable_relative_path: str
    executable_sha256: str
    files: tuple[HermesArtifactFile, ...] = ()
    runtime_id: str = "hermes"
    upstream_commit: str = HERMES_UPSTREAM_COMMIT
    source: str = _HERMES_SOURCE
    license: str = "MIT"
    capabilities: RuntimeCapabilities = field(default_factory=lambda: RuntimeCapabilities(
        messages=True,
        planning=True,
        tools=True,
        file_changes=True,
        shell=True,
        permissions=True,
        cancellation=True,
        resumption=True,
        images=True,
    ))

    def __post_init__(self) -> None:
        if self.runtime_id != "hermes":
            raise ValueError("runtime_id must be hermes")
        if not _valid_version(self.implementation_version):
            raise ValueError("implementation_version is required")
        if not _valid_version(self.acp_protocol_version):
            raise ValueError("acp_protocol_version is required")
        if not _is_safe_relative_path(self.executable_relative_path):
            raise ValueError("executable_relative_path must be a safe relative path")
        if not isinstance(self.executable_sha256, str) or not _SHA256.fullmatch(self.executable_sha256):
            raise ValueError("executable_sha256 must be SHA-256")
        if self.upstream_commit != HERMES_UPSTREAM_COMMIT:
            raise ValueError("upstream_commit must match audited Hermes source")
        if self.source != _HERMES_SOURCE or self.license != "MIT":
            raise ValueError("Hermes source and license are fixed")
        if not isinstance(self.capabilities, RuntimeCapabilities):
            raise ValueError("capabilities must be RuntimeCapabilities")
        if not isinstance(self.files, tuple):
            raise ValueError("artifact files must be a tuple")
        if any(not isinstance(item, HermesArtifactFile) for item in self.files):
            raise ValueError("artifact files must be HermesArtifactFile values")
        paths = [item.relative_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("artifact file paths must be unique")
        if self.files:
            executable = next(
                (item for item in self.files if item.relative_path == self.executable_relative_path),
                None,
            )
            if executable is None or executable.sha256 != self.executable_sha256:
                raise ValueError("artifact files must include the fixed executable")

    @property
    def has_complete_inventory(self) -> bool:
        return bool(self.files)

    def verify_installation(
        self, managed_root: Path, installation: Path, *, require_complete_tree: bool = False,
    ) -> Path:
        root = managed_root.resolve()
        raw_candidate = installation.absolute()
        _reject_reparse_path(root, raw_candidate)
        candidate = raw_candidate.resolve()
        if not _within(candidate, root):
            raise ValueError("installation must be inside managed runtime root")
        if require_complete_tree and not self.files:
            raise ValueError("Hermes installation inventory is unavailable")
        executable = candidate / self.executable_relative_path
        _reject_reparse_path(root, executable)
        if not executable.is_file():
            raise ValueError("Hermes executable is missing")
        digest = sha256(executable.read_bytes()).hexdigest()
        if digest != self.executable_sha256:
            raise ValueError("Hermes executable SHA-256 mismatch")
        if require_complete_tree:
            self._verify_file_inventory(root, candidate)
        return executable

    def _verify_file_inventory(self, root: Path, installation: Path) -> None:
        expected = {item.relative_path: item.sha256 for item in self.files}
        actual: dict[str, Path] = {}
        for path in installation.rglob("*"):
            relative = path.relative_to(installation).as_posix()
            if path.is_symlink() or _is_reparse_point(path):
                raise ValueError("Hermes installation cannot use a reparse point")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError("Hermes installation contains an unsupported file")
            _reject_reparse_path(root, path)
            actual[relative] = path
        for relative in actual:
            if relative not in expected:
                raise ValueError("Hermes installation contains an unexpected file")
        for relative, expected_hash in expected.items():
            path = actual.get(relative)
            if path is None:
                raise ValueError("Hermes installation is missing a required file")
            if sha256(path.read_bytes()).hexdigest() != expected_hash:
                raise ValueError("Hermes installation file SHA-256 mismatch")


def _valid_version(value: object) -> bool:
    return isinstance(value, str) and bool(value) and not any(char.isspace() for char in value)


def _is_safe_relative_path(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return bool(
        path
        and not path.is_absolute()
        and not path.drive
        and ".." not in path.parts
        and len(path.parts) > 1
    )


def _is_safe_artifact_path(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return bool(
        path
        and not path.is_absolute()
        and not path.drive
        and ".." not in path.parts
        and path.parts
    )


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_reparse_path(root: Path, path: Path) -> None:
    if not _within(path.absolute(), root):
        raise ValueError("executable must be inside managed runtime root")
    current = root
    for component in path.relative_to(root).parts:
        current /= component
        if not current.exists():
            return
        if current.is_symlink() or _is_reparse_point(current):
            raise ValueError("Hermes executable cannot use a reparse point")


def _is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(), "st_file_attributes", 0)
    flag = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)
