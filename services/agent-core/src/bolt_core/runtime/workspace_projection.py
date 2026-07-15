"""Workspace projection boundary for managed external runtimes."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import shutil
import stat

_SECRET_NAMES = frozenset({".env", "credentials", "id_rsa", "id_ed25519", "secret"})
_SECRET_DIRECTORIES = frozenset({".aws", ".git", ".ssh"})
_SECRET_SUFFIXES = frozenset({".key", ".pem"})


class WorkspaceProjectionError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceProjection:
    source_workspace: Path
    session_root: Path
    workspace_root: Path
    hermes_home: Path
    home: Path
    temp: Path
    acl_enforced: bool

    @classmethod
    def create(cls, workspace: Path, session_root: Path) -> "WorkspaceProjection":
        try:
            source = _canonical_workspace(workspace)
            root = Path(session_root).resolve(strict=False)
            projection = cls(
                source_workspace=source,
                session_root=root,
                workspace_root=root / "workspace",
                hermes_home=root / "hermes-home",
                home=root / "home",
                temp=root / "temp",
                acl_enforced=False,
            )
            projection._materialize()
            return projection._with_acl()
        except WorkspaceProjectionError:
            raise
        except Exception as error:
            raise WorkspaceProjectionError("workspace_projection_required") from error

    def contains(self, path: Path) -> bool:
        try:
            Path(path).resolve(strict=False).relative_to(self.workspace_root)
            return True
        except ValueError:
            return False

    def validate_runtime_cwd(self, path: Path) -> None:
        if not self.contains(path):
            raise WorkspaceProjectionError("workspace_projection_required")
        _reject_reparse_path(Path(path))

    def with_acl_enforced(self, value: bool) -> "WorkspaceProjection":
        return replace(self, acl_enforced=value)

    def can_restricted_token_read(self, path: Path) -> bool:
        return self.acl_enforced and self.contains(path)

    def cleanup(self) -> None:
        shutil.rmtree(self.session_root, ignore_errors=False)

    def _materialize(self) -> None:
        for directory in (self.workspace_root, self.hermes_home, self.home, self.temp):
            directory.mkdir(parents=True, exist_ok=True)
        _copy_workspace(self.source_workspace, self.workspace_root)
        (self.workspace_root / ".git").mkdir()

    def _with_acl(self) -> "WorkspaceProjection":
        if os.name != "nt":
            return self
        from bolt_core.runtime.windows_acl import enforce_projection_acl

        enforce_projection_acl(self.session_root)
        return replace(self, acl_enforced=True)


def _canonical_workspace(workspace: Path) -> Path:
    raw = os.fspath(workspace)
    if raw.startswith("\\\\"):
        raise WorkspaceProjectionError("workspace_projection_required")
    raw_candidate = Path(workspace).absolute()
    _reject_reparse_path(raw_candidate)
    candidate = raw_candidate.resolve(strict=True)
    if candidate == Path.home().resolve(strict=False):
        raise WorkspaceProjectionError("workspace_projection_required")
    if not candidate.is_dir():
        raise WorkspaceProjectionError("workspace_projection_required")
    return candidate


def _copy_workspace(source: Path, target: Path) -> None:
    for current in source.rglob("*"):
        relative = current.relative_to(source)
        if _is_sensitive(relative):
            continue
        _reject_reparse_path(current)
        destination = target / relative
        if current.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif current.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, destination)
        else:
            raise WorkspaceProjectionError("workspace_projection_required")


def _is_sensitive(path: Path) -> bool:
    lowered = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    if any(part in _SECRET_DIRECTORIES for part in lowered):
        return True
    if name in _SECRET_NAMES or name.startswith(".env."):
        return True
    return path.suffix.lower() in _SECRET_SUFFIXES


def _reject_reparse_path(path: Path) -> None:
    current = Path(path).absolute()
    parts = current.parts
    if not parts:
        raise WorkspaceProjectionError("workspace_projection_required")
    probe = Path(parts[0])
    for part in parts[1:]:
        probe /= part
        if not probe.exists() and not probe.is_symlink():
            continue
        if probe.is_symlink() or _is_reparse_point(probe):
            raise WorkspaceProjectionError("workspace_projection_required")


def _is_reparse_point(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as error:
        raise WorkspaceProjectionError("workspace_projection_required") from error
    attributes = getattr(details, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
