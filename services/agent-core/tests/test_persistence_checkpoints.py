"""Slice E: checkpoints bound to real task revisions, with artifact offloading.

A checkpoint must reference the task's current revision. A stale or mismatched
revision must be rejected. Large tool outputs are not inlined into the
checkpoint payload: only a reference and a summary are stored, and the full
output goes into a controlled artifact file whose path the caller cannot steer.
"""

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    PersistenceConflictError,
)


def _repository(tmp_path) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(tmp_path / "user-data"))


def _seed_task(repository) -> None:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    repository.create_task("task_123", workspace_id, "session_123", "running", {})


def test_checkpoint_matching_current_revision_is_saved(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)

    repository.save_checkpoint("checkpoint_1", "task_123", 0, {"step": 1})

    checkpoints = repository.list_checkpoints("task_123")
    assert [c["id"] for c in checkpoints] == ["checkpoint_1"]
    assert checkpoints[0]["task_revision"] == 0


def test_checkpoint_after_task_update_tracks_new_revision(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)
    repository.update_task("task_123", expected_revision=0, status="running")

    repository.save_checkpoint("checkpoint_2", "task_123", 1, {"step": 2})

    assert repository.list_checkpoints("task_123")[0]["task_revision"] == 1


def test_checkpoint_with_stale_revision_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)
    repository.update_task("task_123", expected_revision=0, status="running")

    with pytest.raises(PersistenceConflictError):
        repository.save_checkpoint("checkpoint_stale", "task_123", 0, {"step": 1})

    assert repository.list_checkpoints("task_123") == []


def test_checkpoint_with_future_revision_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)

    with pytest.raises(PersistenceConflictError):
        repository.save_checkpoint("checkpoint_future", "task_123", 5, {"step": 1})

    assert repository.list_checkpoints("task_123") == []


def test_checkpoint_for_missing_task_is_rejected(tmp_path):
    repository = _repository(tmp_path)

    with pytest.raises(KeyError):
        repository.save_checkpoint("checkpoint_orphan", "task_absent", 0, {})
