import sqlite3

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository, PersistenceConflictError


def _repository(root):
    return ControlPlaneRepository(Database.open(root))


def _seed(repository, path="C:/Projects/A"):
    workspace_id = repository.save_workspace(path)
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})
    repository.create_queue_item("eq_123", workspace_id, "approved", {"closure_id": "cl_123"})
    return workspace_id


def _payload(**overrides):
    payload = {
        "id": "eh_123",
        "queue_item_id": "eq_123",
        "closure_id": "cl_123",
        "kind": "manual_review",
        "status": "ready_for_manual_action",
        "handoff_type": "manual_review",
        "title": "Review",
        "instruction": "Review safely",
        "command": None,
        "goal_objective": "Review",
        "run_id": None,
        "goal_id": None,
        "created_at": 1.0,
        "updated_at": 1.0,
        "result": "",
        "permission_request_id": None,
        "permission_status": "not_requested",
        "bridge_error": "",
        "permission_workspace": "",
    }
    payload.update(overrides)
    return payload


def test_handoff_can_be_created_loaded_updated_and_rebuilt(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)

    repository.create_handoff_record("eh_123", workspace_id, "eq_123", "cl_123", "ready", _payload())
    updated = repository.update_handoff_record("eh_123", 0, "completed", _payload(result="done", status="completed"))
    rebuilt = _repository(root)

    assert updated["revision"] == 1
    assert rebuilt.load_handoff_record("eh_123")["status"] == "completed"


def test_handoff_revision_conflict_and_workspace_isolation(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_a = _seed(repository, "C:/Projects/A")
    workspace_b = _repository(tmp_path / "other-data")
    workspace_b_id = _seed(workspace_b, "C:/Projects/B")
    repository.create_handoff_record("eh_123", workspace_a, "eq_123", "cl_123", "ready", _payload())

    with pytest.raises(PersistenceConflictError):
        repository.update_handoff_record("eh_123", 9, "completed")
    assert repository.list_handoff_records(workspace_a)[0]["id"] == "eh_123"
    assert repository.list_handoff_records(workspace_b_id) == []


def test_handoff_rejects_secret_and_invalid_workspace_link(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_a = _seed(repository, "C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")

    with pytest.raises(ValueError):
        repository.create_handoff_record(
            "eh_secret", workspace_a, "eq_123", "cl_123", "ready",
            _payload(result="Bearer ghp_secretcanary123456789"),
        )
    with pytest.raises(ValueError):
        repository.create_handoff_record("eh_wrong_workspace", workspace_b, "eq_123", "cl_123", "ready", _payload())
    assert repository.list_handoff_records(workspace_a) == []
    assert b"ghp_secretcanary123456789" not in repository.database.path.read_bytes()
