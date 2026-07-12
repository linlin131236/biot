"""Controlled artifact storage for large tool outputs.

Full tool output is written to a controlled file under the data root; only a
bounded reference (id, sha256, size, summary) is returned for inlining into a
checkpoint or task JSON payload. Callers cannot steer the artifact path: the
task id must be a plain identifier and artifact ids are content-addressed and
generated internally. Content addressing makes ``load`` self-verifying: the
sha256 is embedded in the id, so tampering is detected without the reference.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from bolt_core.atomic_write import atomic_write_text
from bolt_core.persistence.models import validate_identifier, validate_message_content

_SUMMARY_LIMIT = 512
_ARTIFACT_PREFIX = "artifact_"


class ArtifactStore:
    def __init__(self, data_root: Path) -> None:
        self._root = Path(data_root).resolve() / "artifacts"

    def store(self, task_id: str, output: str) -> dict:
        validate_identifier(task_id)
        if not isinstance(output, str):
            raise ValueError("artifact output must be text")
        validate_message_content(output)
        data = output.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        artifact_id = f"{_ARTIFACT_PREFIX}{digest}"
        target = self._resolved_path(artifact_id)
        atomic_write_text(target, output)
        return {
            "artifact_id": artifact_id,
            "task_id": task_id,
            "size": len(data),
            "sha256": digest,
            "summary": output[:_SUMMARY_LIMIT],
        }

    def path_for(self, artifact_id: str) -> Path:
        return self._resolved_path(artifact_id)

    def load(self, artifact_id: str) -> str:
        path = self._resolved_path(artifact_id)
        if not path.exists():
            raise KeyError(artifact_id)
        data = path.read_bytes()
        expected = artifact_id[len(_ARTIFACT_PREFIX):]
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("artifact integrity check failed")
        return data.decode("utf-8")

    def _resolved_path(self, artifact_id: str) -> Path:
        validate_identifier(artifact_id)
        if not artifact_id.startswith(_ARTIFACT_PREFIX):
            raise ValueError("invalid artifact id")
        candidate = (self._root / artifact_id).resolve()
        if candidate.parent != self._root:
            raise ValueError("artifact path escapes the data root")
        return candidate
