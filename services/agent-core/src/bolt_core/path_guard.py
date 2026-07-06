from dataclasses import dataclass
from pathlib import Path


SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "secret"}
SECRET_DIRS = {".ssh", ".aws"}
SECRET_SUFFIXES = {".pem", ".key"}


@dataclass(frozen=True)
class PathCheck:
    allowed: bool
    path: Path
    reason: str


class PathGuard:
    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace).resolve()

    def check(self, target: str) -> PathCheck:
        path = (self.workspace / target).resolve(strict=False)
        if not self._inside_workspace(path):
            return PathCheck(False, path, "path outside workspace")
        if self._is_secret(path):
            return PathCheck(False, path, "secret path denied")
        return PathCheck(True, path, "workspace path allowed")

    def _inside_workspace(self, path: Path) -> bool:
        try:
            path.relative_to(self.workspace)
            return True
        except ValueError:
            return False

    def _is_secret(self, path: Path) -> bool:
        lowered = [part.lower() for part in path.parts]
        name = path.name.lower()
        if any(part in SECRET_DIRS for part in lowered):
            return True
        if name in SECRET_NAMES or name.startswith(".env."):
            return True
        return path.suffix.lower() in SECRET_SUFFIXES
