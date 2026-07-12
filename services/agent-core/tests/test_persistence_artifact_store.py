"""Slice E2: large tool outputs offloaded to controlled artifact files.

Full tool output is not inlined into checkpoint/task JSON. It is written to a
controlled artifact file under the data root, and only a reference (artifact id
+ sha256 + size + summary) is kept in the JSON payload. The caller cannot steer
the artifact path (no traversal, no absolute path, no workspace_id control).
"""

import hashlib
import json

import pytest

from bolt_core.persistence.artifact_store import ArtifactStore


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _store(tmp_path) -> ArtifactStore:
    return ArtifactStore(tmp_path / "user-data")


def test_store_writes_full_output_and_returns_reference(tmp_path):
    store = _store(tmp_path)
    payload = "x" * 50_000

    ref = store.store("task_123", payload)

    assert ref["artifact_id"]
    assert ref["size"] == len(payload.encode("utf-8"))
    assert ref["sha256"] == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    # Only a bounded summary is kept in the reference, never the full payload.
    assert len(ref["summary"]) <= 512
    assert "full" not in ref


def test_stored_artifact_can_be_loaded_back_by_id(tmp_path):
    store = _store(tmp_path)
    payload = "hello world\n" * 1000

    ref = store.store("task_123", payload)
    loaded = store.load(ref["artifact_id"])

    assert loaded == payload


def test_artifact_reference_is_json_safe_for_checkpoint_payload(tmp_path):
    store = _store(tmp_path)
    ref = store.store("task_123", "y" * 20_000)

    # The reference must round-trip through the repository JSON validation, i.e.
    # it must be a plain JSON object with no sensitive keys.
    encoded = json.dumps({"tool_output": ref})
    assert json.loads(encoded)["tool_output"]["artifact_id"] == ref["artifact_id"]


@pytest.mark.parametrize(
    "malicious_task_id",
    [
        "../escape",
        "..\\escape",
        "a/b",
        "a\\b",
        "/abs",
        "C:/abs",
        "",
    ],
)
def test_artifact_task_id_cannot_traverse_or_escape_data_root(malicious_task_id, tmp_path):
    store = _store(tmp_path)

    with pytest.raises(ValueError):
        store.store(malicious_task_id, "payload")


def test_artifact_files_live_under_data_root_only(tmp_path):
    root = tmp_path / "user-data"
    store = ArtifactStore(root)

    ref = store.store("task_123", "z" * 10_000)
    artifact_path = store.path_for(ref["artifact_id"])

    resolved_root = root.resolve()
    assert resolved_root in artifact_path.resolve().parents


def test_store_rejects_secret_without_writing_artifact(tmp_path):
    store = _store(tmp_path)

    with pytest.raises(ValueError):
        store.store("task_123", f"Bearer {_SECRET_CANARY}")

    artifacts = tmp_path / "user-data" / "artifacts"
    assert not artifacts.exists() or _SECRET_CANARY.encode() not in b"".join(
        path.read_bytes() for path in artifacts.iterdir()
    )


def test_load_rejects_traversal_artifact_id(tmp_path):
    store = _store(tmp_path)

    with pytest.raises(ValueError):
        store.load("../../etc/passwd")


def test_stored_artifact_detects_corruption_on_load(tmp_path):
    store = _store(tmp_path)
    ref = store.store("task_123", "content" * 500)
    path = store.path_for(ref["artifact_id"])

    path.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="integrity"):
        store.load(ref["artifact_id"])
