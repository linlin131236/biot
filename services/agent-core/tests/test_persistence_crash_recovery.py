"""Slice D: crash recovery through the unified ControlPlaneRepository.

On startup, tasks left in a non-terminal, in-flight state (running or
waiting_approval) must be surfaced for recovery rather than silently treated as
completed. Recovery must not auto-approve a pending human approval, and the
scan must work against a freshly rebuilt repository over the same user data.
"""

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.recovery import RecoveryScanner
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    TaskTerminalStateError,
)


def _repository(root) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(root))


def _seed(repository) -> str:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    return workspace_id


def _create_runtime_task(repository, workspace_id: str, task_id: str, status: str, payload: dict) -> None:
    repository.create_task(task_id, workspace_id, "session_123", status, payload)
    repository.create_runtime_session(
        f"runtime_{task_id}", task_id, "bolt-native", task_id, status,
    )


def test_recovery_scan_surfaces_running_and_waiting_tasks(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    _create_runtime_task(repository, workspace_id, "task_run", "running", {})
    _create_runtime_task(repository, workspace_id, "task_wait", "waiting_approval", {})
    repository.create_task("task_done", workspace_id, "session_123", "completed", {})

    # Simulate a crash + restart: brand new Database + repository over same root.
    rebuilt = _repository(root)
    scanner = RecoveryScanner(rebuilt)
    recovered = scanner.recover_workspace(workspace_id)

    assert {t["id"] for t in recovered} == {"task_run", "task_wait"}


def test_recovery_marks_running_tasks_as_recovering_not_completed(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    _create_runtime_task(repository, workspace_id, "task_run", "running", {})

    rebuilt = _repository(root)
    RecoveryScanner(rebuilt).recover_workspace(workspace_id)

    task = rebuilt.load_task("task_run")
    assert task["status"] == "recovering"
    session = next(
        item for item in rebuilt.list_runtime_sessions(workspace_id)
        if item["task_id"] == "task_run"
    )
    assert session["status"] == "recovering"
    assert task["revision"] == 1


def test_recovery_does_not_touch_completed_task(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    repository.create_task("task_done", workspace_id, "session_123", "completed", {})

    rebuilt = _repository(root)
    RecoveryScanner(rebuilt).recover_workspace(workspace_id)

    task = rebuilt.load_task("task_done")
    assert task["status"] == "completed"
    assert task["revision"] == 0


def test_waiting_approval_recovers_without_auto_approving(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    _create_runtime_task(
        repository, workspace_id, "task_wait", "waiting_approval",
        {"request": "delete files"},
    )

    rebuilt = _repository(root)
    RecoveryScanner(rebuilt).recover_workspace(workspace_id)

    task = rebuilt.load_task("task_wait")
    # It must move to recovering, never to an approved/running state.
    assert task["status"] == "recovering"
    assert task["status"] not in ("approved", "running", "completed")
    # The original approval request payload must be preserved for human review.
    assert task["payload"] == {"request": "delete files"}


def test_recovering_task_is_not_terminal_and_can_progress(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    _create_runtime_task(repository, workspace_id, "task_run", "running", {})

    rebuilt = _repository(root)
    RecoveryScanner(rebuilt).recover_workspace(workspace_id)

    # A recovering task must still be updatable (it is not a terminal state).
    updated = rebuilt.update_task("task_run", expected_revision=1, status="completed")
    assert updated["status"] == "completed"


def test_second_recovery_is_idempotent(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    _create_runtime_task(repository, workspace_id, "task_run", "running", {})

    rebuilt = _repository(root)
    RecoveryScanner(rebuilt).recover_workspace(workspace_id)
    # Re-scan: an already-recovering task stays recovering, not double-bumped
    # into a terminal or approved state.
    again = RecoveryScanner(rebuilt).recover_workspace(workspace_id)

    assert {t["id"] for t in again} == {"task_run"}
    assert rebuilt.load_task("task_run")["status"] == "recovering"
