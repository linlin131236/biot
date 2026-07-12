"""Slice B: task lifecycle through the unified ControlPlaneRepository.

Tasks are created, updated and driven to a terminal state exclusively through
the repository. Revision conflicts must not silently overwrite, and a terminal
task must not be reverted by a later normal update.
"""

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    PersistenceConflictError,
    TaskTerminalStateError,
)


def _repository(tmp_path) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(tmp_path / "user-data"))


def _seed_task(repository) -> str:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    repository.create_task("task_123", workspace_id, "session_123", "running", {})
    return workspace_id


def test_task_can_be_loaded_after_creation(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)

    task = repository.load_task("task_123")

    assert task["id"] == "task_123"
    assert task["status"] == "running"
    assert task["revision"] == 0
    assert task["payload"] == {}


def test_load_missing_task_raises_keyerror(tmp_path):
    repository = _repository(tmp_path)

    with pytest.raises(KeyError):
        repository.load_task("task_absent")


def test_update_task_increments_revision_and_persists_status(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)

    updated = repository.update_task(
        "task_123", expected_revision=0, status="waiting_approval",
        payload={"note": "pending human review"},
    )

    assert updated["status"] == "waiting_approval"
    assert updated["revision"] == 1
    assert updated["payload"] == {"note": "pending human review"}
    assert repository.load_task("task_123")["revision"] == 1


def test_update_task_revision_conflict_does_not_overwrite(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)

    with pytest.raises(PersistenceConflictError):
        repository.update_task("task_123", expected_revision=7, status="completed")

    task = repository.load_task("task_123")
    assert task["status"] == "running"
    assert task["revision"] == 0


def test_terminal_task_cannot_be_reverted_by_normal_update(tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)
    repository.update_task("task_123", expected_revision=0, status="completed")

    with pytest.raises(TaskTerminalStateError):
        repository.update_task("task_123", expected_revision=1, status="running")

    task = repository.load_task("task_123")
    assert task["status"] == "completed"
    assert task["revision"] == 1


@pytest.mark.parametrize("terminal", ["completed", "failed", "cancelled"])
def test_terminal_task_rejects_any_further_status_change(terminal, tmp_path):
    repository = _repository(tmp_path)
    _seed_task(repository)
    repository.update_task("task_123", expected_revision=0, status=terminal)

    with pytest.raises(TaskTerminalStateError):
        repository.update_task("task_123", expected_revision=1, status="running")


def test_list_tasks_filters_by_workspace_and_status(tmp_path):
    repository = _repository(tmp_path)
    workspace_a = repository.save_workspace("C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")
    repository.create_task("task_a_run", workspace_a, None, "running", {})
    repository.create_task("task_a_done", workspace_a, None, "completed", {})
    repository.create_task("task_b_run", workspace_b, None, "running", {})

    running_a = repository.list_tasks(workspace_a, statuses=["running"])

    assert [t["id"] for t in running_a] == ["task_a_run"]
    all_a = repository.list_tasks(workspace_a)
    assert {t["id"] for t in all_a} == {"task_a_run", "task_a_done"}
