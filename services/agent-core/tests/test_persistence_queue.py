"""Slice 3-queue (repository layer): execution queue items persist through a
dedicated ControlPlaneRepository table (execution_queue_items), not the legacy
execution-audit JSON.

A queue item is created, updated with CAS, and listed per workspace/closure.
Revision conflicts must not silently overwrite. Secret content must be rejected
without writing a canary. Items survive a repository rebuild.
"""

import sqlite3

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    PersistenceConflictError,
)


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _repository(root) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(root))


def _seed(repository) -> tuple[str, str]:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})
    return workspace_id, "cl_123"


def _payload(**overrides) -> dict:
    payload = {
        "closure_id": "cl_123",
        "kind": "verification_command",
        "title": "run tests",
        "description": "pytest -q",
        "risk": "read_only",
        "command": "pytest -q",
        "reason": "",
        "result": "",
        "created_at": 1.0,
    }
    payload.update(overrides)
    return payload


def test_queue_item_can_be_created_and_loaded(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id, _ = _seed(repository)

    repository.create_queue_item("eq_0", workspace_id, "pending", _payload())

    item = repository.load_queue_item("eq_0")
    assert item["id"] == "eq_0"
    assert item["status"] == "pending"
    assert item["revision"] == 0
    assert item["payload"]["title"] == "run tests"


def test_load_missing_queue_item_raises_keyerror(tmp_path):
    repository = _repository(tmp_path / "user-data")

    with pytest.raises(KeyError):
        repository.load_queue_item("eq_absent")


def test_update_queue_item_increments_revision(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id, _ = _seed(repository)
    repository.create_queue_item("eq_0", workspace_id, "pending", _payload())

    updated = repository.update_queue_item(
        "eq_0", expected_revision=0, status="approved", payload=_payload(),
    )

    assert updated["status"] == "approved"
    assert updated["revision"] == 1
    assert repository.load_queue_item("eq_0")["revision"] == 1


def test_update_queue_item_revision_conflict_does_not_overwrite(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id, _ = _seed(repository)
    repository.create_queue_item("eq_0", workspace_id, "pending", _payload())

    with pytest.raises(PersistenceConflictError):
        repository.update_queue_item("eq_0", expected_revision=9, status="approved")

    item = repository.load_queue_item("eq_0")
    assert item["status"] == "pending"
    assert item["revision"] == 0


def test_list_queue_items_filters_by_workspace(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_a = repository.save_workspace("C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")
    repository.create_closure("cl_a", workspace_a, "pending", {"events": []})
    repository.create_closure("cl_b", workspace_b, "pending", {"events": []})
    repository.create_queue_item("eq_a", workspace_a, "pending", _payload(closure_id="cl_a"))
    repository.create_queue_item("eq_b", workspace_b, "pending", _payload(closure_id="cl_b"))

    ids_a = [i["id"] for i in repository.list_queue_items(workspace_a)]
    assert ids_a == ["eq_a"]


def test_queue_items_survive_repository_rebuild(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id, _ = _seed(repository)
    repository.create_queue_item("eq_0", workspace_id, "approved", _payload())

    rebuilt = _repository(root)
    item = rebuilt.load_queue_item("eq_0")
    assert item["status"] == "approved"
    assert item["payload"]["command"] == "pytest -q"


@pytest.mark.parametrize(
    "payload",
    [
        _payload(title=f"key ghp_{_SECRET_CANARY}{'A' * 20}"),
        _payload(result=f"Bearer {_SECRET_CANARY}"),
    ],
    ids=["title-secret", "result-secret"],
)
def test_queue_item_rejects_secret_without_writing_canary(payload, tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id, _ = _seed(repository)

    with pytest.raises(ValueError) as caught:
        repository.create_queue_item("eq_secret", workspace_id, "pending", payload)

    assert _SECRET_CANARY not in str(caught.value)
    assert _SECRET_CANARY.encode() not in repository.database.path.read_bytes()


def test_queue_item_create_rejects_duplicate_id(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id, _ = _seed(repository)
    repository.create_queue_item("eq_0", workspace_id, "pending", _payload())

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_queue_item("eq_0", workspace_id, "pending", _payload())
