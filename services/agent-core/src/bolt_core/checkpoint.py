"""Checkpoint service: snapshot run state for resume.

Does not copy large files or secrets.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from bolt_core.persistence.artifact_store import ArtifactStore

_MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
_SECRET_PATTERN = re.compile(r"sk-[a-zA-Z0-9]{20,}")
_CP_ID_PATTERN = re.compile(r"^cp_[a-f0-9]{8}$")
_SECRET_PATH_PARTS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials",
    "secrets",
    "secret",
    "id_rsa",
    "id_ed25519",
}


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
    def __init__(
        self, workspace: str = "", repository=None,
        workspace_id: str | None = None, artifact_store: ArtifactStore | None = None,
    ) -> None:
        if repository is not None and workspace_id is None:
            raise ValueError("repository-backed checkpoints require a workspace_id")
        self._workspace = workspace
        self._repository = repository
        self._workspace_id = workspace_id
        self._artifacts = artifact_store
        self._dir = Path(workspace) / ".bolt" / "checkpoints" if workspace else Path(
            ".bolt") / "checkpoints"
        if repository is None:
            self._dir.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str, goal_id: str,
               changed_files: list[str] | None = None,
               constraints: list[str] | None = None,
               pending_permissions: list[str] | None = None,
               evidence_refs: list[str] | None = None,
               task_revision: int | None = None) -> Checkpoint:
        cp_id = f"cp_{uuid4().hex[:8]}"
        contents = {}
        if changed_files and self._workspace:
            ws = Path(self._workspace).resolve()
            for f in changed_files:
                if _is_secret_path(f):
                    continue
                fp = (ws / f).resolve()
                try:
                    fp.relative_to(ws)
                except ValueError:
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
        if self._repository is not None:
            return self._persist_repository(cp, task_revision)
        # Persist
        cp_path = self._dir / f"{cp_id}.json"
        cp_path.write_text(json.dumps(cp.to_dict(), indent=2), encoding="utf-8")
        return cp

    def load(self, cp_id: str) -> Checkpoint | None:
        if not _CP_ID_PATTERN.match(cp_id):
            return None
        if self._repository is not None:
            try:
                record = self._repository.load_checkpoint(cp_id)
            except KeyError:
                return None
            payload = dict(record["payload"])
            return Checkpoint(
                id=record["id"],
                run_id=payload.get("run_id", ""),
                goal_id=record["task_id"],
                changed_files=payload.get("changed_files", []),
                file_contents=self._load_artifacts(payload.get("file_contents")),
                constraints=payload.get("constraints", []),
                pending_permissions=payload.get("pending_permissions", []),
                evidence_refs=payload.get("evidence_refs", []),
            )
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

    def _persist_repository(self, checkpoint: Checkpoint, task_revision: int | None) -> Checkpoint:
        task = self._repository.load_task(checkpoint.goal_id)
        revision = task["revision"] if task_revision is None else task_revision
        file_contents = checkpoint.file_contents or {}
        if self._artifacts is not None:
            file_contents = {
                path: {
                    "artifact_id": self._artifacts.store(checkpoint.goal_id, content)["artifact_id"],
                    "summary": content[:512],
                }
                for path, content in file_contents.items()
            }
        payload = checkpoint.to_dict()
        payload.pop("id", None)
        payload["file_contents"] = file_contents or None
        self._repository.save_checkpoint(
            checkpoint.id, checkpoint.goal_id, revision, payload,
        )
        return checkpoint

    def _load_artifacts(self, value: object) -> dict[str, str] | None:
        if not isinstance(value, dict):
            return None
        if self._artifacts is None:
            return {
                path: content for path, content in value.items()
                if isinstance(content, str)
            } or None
        loaded: dict[str, str] = {}
        for path, reference in value.items():
            if not isinstance(reference, dict):
                continue
            artifact_id = reference.get("artifact_id")
            if isinstance(artifact_id, str):
                loaded[path] = self._artifacts.load(artifact_id)
        return loaded or None

    def restore(self, cp_id: str, confirm_restore: bool = False) -> dict:
        if not confirm_restore:
            return {
                "status": "confirmation_required",
                "checkpoint_id": cp_id,
                "restored_files": [],
                "skipped_files": [],
                "reason": "restore requires explicit confirmation",
            }

        cp = self.load(cp_id)
        if cp is None:
            return {
                "status": "not_found",
                "checkpoint_id": cp_id,
                "restored_files": [],
                "skipped_files": [],
                "reason": "checkpoint not found",
            }

        restored_files: list[str] = []
        skipped_files: list[str] = []
        file_contents = cp.file_contents or {}
        ws = Path(self._workspace).resolve() if self._workspace else Path.cwd().resolve()

        for rel_path in cp.changed_files:
            if _is_secret_path(rel_path):
                skipped_files.append(rel_path)
                continue
            content = file_contents.get(rel_path)
            if content is None:
                skipped_files.append(rel_path)
                continue
            target = (ws / rel_path).resolve()
            try:
                target.relative_to(ws)
            except ValueError:
                skipped_files.append(rel_path)
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            except OSError:
                skipped_files.append(rel_path)
                continue
            restored_files.append(rel_path)

        return {
            "status": "restored",
            "checkpoint_id": cp.id,
            "restored_files": restored_files,
            "skipped_files": skipped_files,
        }

    def project_status(self) -> dict:
        """Return project status. Uses workspace .bolt cache if available."""
        status = {"commits": 0, "uncommitted_changes": False}
        # Delegated to shell_executor via harness; checkpoint only stores
        return status


def _is_secret_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    return bool(parts & _SECRET_PATH_PARTS)
