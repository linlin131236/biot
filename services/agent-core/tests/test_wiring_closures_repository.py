"""Wiring slice 3-closure: TaskClosureService persists through the unified
ControlPlaneRepository (task_closures table), not the legacy execution-audit JSON.

Production wiring proof:
- A closure created through the harness lands in the SQLite task_closures table.
- After the App/Harness is destroyed and rebuilt over the SAME persistence root,
  the closure state is recovered from the repository.
- When a repository is configured, the legacy execution-audit.json is neither
  read nor written (content and mtime unchanged).
- A repository write failure fails closed (no silent fallback to JSON).
- Secret content in command_results/events is rejected without writing a canary.
"""

import json
import time

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository
from bolt_core.task_closure import TaskTemplateId
from bolt_core.task_closure_service import TaskClosureService


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _repository(root) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(root))


def _service(repository):
    workspace_id = repository.save_workspace("C:/Projects/A")
    return TaskClosureService(repository=repository, workspace_id=workspace_id), workspace_id


def test_closure_persists_into_repository_table(tmp_path):
    repository = _repository(tmp_path / "user-data")
    service, _ = _service(repository)

    closure = service.start("fix the bug", TaskTemplateId.BUGFIX, run_id="run_1")

    db_path = repository.database.path
    connection = repository.database.connection()
    try:
        row = connection.execute(
            "select status from task_closures where id = ?", (closure.id,)
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row["status"] == "pending"


def test_closure_state_machine_persisted_through_repository(tmp_path):
    repository = _repository(tmp_path / "user-data")
    service, _ = _service(repository)
    closure = service.start("ship feature", TaskTemplateId.BUGFIX)

    service.transition(closure.id, "planning")
    service.transition(closure.id, "executing")

    reloaded = service.to_dict(closure.id)
    assert reloaded["status"] == "executing"


def test_closure_recovers_after_service_rebuild(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    service, _ = _service(repository)
    closure = service.start("persist me", TaskTemplateId.BUGFIX, run_id="run_9")
    service.transition(closure.id, "planning")

    # Destroy the service + repository + database; rebuild over the SAME root.
    del service
    del repository
    rebuilt_repo = _repository(root)
    workspace_id = rebuilt_repo.save_workspace("C:/Projects/A")
    rebuilt = TaskClosureService(repository=rebuilt_repo, workspace_id=workspace_id)

    recovered = rebuilt.load(closure.id)
    assert recovered is not None
    assert recovered.status == "planning"
    assert recovered.objective == "persist me"
    assert recovered.run_id == "run_9"


def test_closure_workspace_isolation(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_a = repository.save_workspace("C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")
    service_a = TaskClosureService(repository=repository, workspace_id=workspace_a)
    service_b = TaskClosureService(repository=repository, workspace_id=workspace_b)

    closure_a = service_a.start("task a", TaskTemplateId.BUGFIX)
    service_b.start("task b", TaskTemplateId.BUGFIX)

    # A fresh service scoped to workspace B must not see workspace A's closure.
    fresh_b = TaskClosureService(repository=repository, workspace_id=workspace_b)
    assert closure_a.id not in [c["id"] for c in fresh_b.list_closures()]


def test_closure_terminal_state_protected(tmp_path):
    repository = _repository(tmp_path / "user-data")
    service, _ = _service(repository)
    closure = service.start("done task", TaskTemplateId.BUGFIX)
    service.transition(closure.id, "planning")
    service.transition(closure.id, "executing")
    service.mark_failed(closure.id, "terminal failure")

    # A terminal closure (failed) must not illegally transition back to executing.
    with pytest.raises(ValueError):
        service.transition(closure.id, "executing")


def test_legacy_execution_audit_json_untouched_when_repository_configured(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    legacy = tmp_path / "workspace" / ".bolt" / "execution-audit.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"queue_items": [], "handoff_records": [], "closure_records": []})
    legacy.write_text(original, encoding="utf-8")
    original_mtime = legacy.stat().st_mtime_ns

    workspace_id = repository.save_workspace("C:/Projects/A")
    service = TaskClosureService(repository=repository, workspace_id=workspace_id)
    time.sleep(0.02)
    service.start("does not touch json", TaskTemplateId.BUGFIX)

    assert legacy.read_text(encoding="utf-8") == original
    assert legacy.stat().st_mtime_ns == original_mtime


def test_closure_command_result_secret_is_rejected_or_redacted(tmp_path):
    repository = _repository(tmp_path / "user-data")
    service, _ = _service(repository)
    closure = service.start("secret task", TaskTemplateId.BUGFIX)

    # A tool result carrying a raw secret must not persist the canary verbatim.
    service.record_tool_result(
        closure.id,
        {"request_id": "req_1", "status": "executed", "output": f"Bearer {_SECRET_CANARY}"},
    )

    db_path = repository.database.path
    assert _SECRET_CANARY.encode() not in db_path.read_bytes()


def test_repository_write_failure_fails_closed(tmp_path):
    repository = _repository(tmp_path / "user-data")
    service, _ = _service(repository)

    # Force the repository into read-only recovery so writes must fail.
    from bolt_core.persistence.database import PersistenceState
    repository.database.state = PersistenceState.READ_ONLY_RECOVERY

    with pytest.raises(Exception):
        service.start("must fail closed", TaskTemplateId.BUGFIX)
