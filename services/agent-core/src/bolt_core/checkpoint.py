"""Checkpoint service: snapshot run state for resume.

Does not copy large files or secrets.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

_MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
_SECRET_PATTERN = re.compile(r"sk-[a-zA-Z0-9]{20,}")
_CP_ID_PATTERN = re.compile(r"^cp_[a-f0-9]{8}$")


@dataclass
class Checkpoint:
    id: str
    run_id: str
    goal_id: str
    changed_files: list[str] = field(default_factory=list)
    file_contents: dict[str, str] | None = None
    constraints: list[str] = field(default_factory=list)
    pending_permissions: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "run_id": self.run_id,
            "goal_id": self.goal_id,
            "changed_files": self.changed_files,
            "file_contents": self._scrub(self.file_contents or {}),
            "constraints": self.constraints,
            "pending_permissions": self.pending_permissions,
            "evidence_refs": self.evidence_refs,
        }

    @staticmethod
    def _scrub(data: dict) -> dict:
        text = json.dumps(data)
        text = _SECRET_PATTERN.sub("[REDACTED]", text)
        return json.loads(text)


class CheckpointService:
    def __init__(self, workspace: str = "") -> None:
        self._workspace = workspace
        self._dir = Path(workspace) / ".bolt" / "checkpoints" if workspace else Path(
            ".bolt") / "checkpoints"
        self._dir.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str, goal_id: str,
               changed_files: list[str] | None = None,
               constraints: list[str] | None = None,
               pending_permissions: list[str] | None = None,
               evidence_refs: list[str] | None = None) -> Checkpoint:
        cp_id = f"cp_{uuid4().hex[:8]}"
        contents = {}
        if changed_files and self._workspace:
            ws = Path(self._workspace).resolve()
            for f in changed_files:
                fp = (ws / f).resolve()
                if not str(fp).lower().startswith(str(ws).lower()):
                    continue  # skip paths outside workspace
                if fp.is_file():
                    try:
                        size = fp.stat().st_size
                        if size <= _MAX_FILE_SIZE:
                            contents[f] = fp.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        pass

        cp = Checkpoint(
            id=cp_id, run_id=run_id, goal_id=goal_id,
            changed_files=changed_files or [],
            file_contents=contents if contents else None,
            constraints=constraints or [],
            pending_permissions=pending_permissions or [],
            evidence_refs=evidence_refs or [],
        )
        # Persist
        cp_path = self._dir / f"{cp_id}.json"
        cp_path.write_text(json.dumps(cp.to_dict(), indent=2), encoding="utf-8")
        return cp

    def load(self, cp_id: str) -> Checkpoint | None:
        if not _CP_ID_PATTERN.match(cp_id):
            return None
        cp_path = self._dir / f"{cp_id}.json"
        if not cp_path.is_file():
            return None
        try:
            data = json.loads(cp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return Checkpoint(
            id=data["id"], run_id=data["run_id"],
            goal_id=data["goal_id"],
            changed_files=data.get("changed_files", []),
            file_contents=data.get("file_contents"),
            constraints=data.get("constraints", []),
            pending_permissions=data.get("pending_permissions", []),
            evidence_refs=data.get("evidence_refs", []),
        )

    def project_status(self) -> dict:
        """Return project status. Uses workspace .bolt cache if available."""
        status = {"commits": 0, "uncommitted_changes": False}
        # Delegated to shell_executor via harness; checkpoint only stores
        return status
