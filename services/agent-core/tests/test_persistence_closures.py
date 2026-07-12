"""Slice 3-closure (repository layer): task closures persist through a dedicated
ControlPlaneRepository table (task_closures), not the legacy execution-audit JSON.

A closure is created, updated with CAS, and listed per workspace. Revision
conflicts must not silently overwrite. Secret content must be rejected without
writing a canary. Closures survive a repository rebuild over the same data root.
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


def _seed(repository) -> str:
    return repository.save_workspace("C:/Projects/A")


def test_closure_can_be_created_and_loaded(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)

    repository.create_closure(
        "cl_123", workspace_id, "pending",
        {"objective": "fix bug", "template_id": "bugfix", "events": []},
    )

    closure = repository.load_closure("cl_123")
    assert closure["id"] == "cl_123"
    assert closure["status"] == "pending"
    assert closure["revision"] == 0
    assert closure["payload"]["objective"] == "fix bug"


def test_load_missing_closure_raises_keyerror(tmp_path):
    repository = _repository(tmp_path / "user-data")

    with pytest.raises(KeyError):
        repository.load_closure("cl_absent")


def test_update_closure_increments_revision(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})

    updated = repository.update_closure(
        "cl_123", expected_revision=0, status="planning",
        payload={"events": [{"type": "transition"}]},
    )

    assert updated["status"] == "planning"
    assert updated["revision"] == 1
    assert repository.load_closure("cl_123")["revision"] == 1


def test_update_closure_revision_conflict_does_not_overwrite(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})

    with pytest.raises(PersistenceConflictError):
        repository.update_closure("cl_123", expected_revision=9, status="planning")

    closure = repository.load_closure("cl_123")
    assert closure["status"] == "pending"
    assert closure["revision"] == 0


def test_list_closures_filters_by_workspace(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_a = repository.save_workspace("C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")
    repository.create_closure("cl_a", workspace_a, "pending", {"events": []})
    repository.create_closure("cl_b", workspace_b, "pending", {"events": []})

    ids_a = [c["id"] for c in repository.list_closures(workspace_a)]
    assert ids_a == ["cl_a"]


def test_closures_survive_repository_rebuild(tmp_path):
    root = tmp_path / "user-data"
    repository = _repository(root)
    workspace_id = _seed(repository)
    repository.create_closure(
        "cl_123", workspace_id, "executing",
        {"objective": "persist me", "events": []},
    )

    rebuilt = _repository(root)
    closure = rebuilt.load_closure("cl_123")
    assert closure["status"] == "executing"
    assert closure["payload"]["objective"] == "persist me"


@pytest.mark.parametrize(
    "payload",
    [
        {"objective": f"key ghp_{_SECRET_CANARY}{'A' * 20}", "events": []},
        {"events": [], "apiKey": _SECRET_CANARY},
        {"command_results": [f"Bearer {_SECRET_CANARY}"], "events": []},
    ],
    ids=["objective-secret", "sensitive-key", "command-result-secret"],
)
def test_closure_rejects_secret_without_writing_canary(payload, tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)

    with pytest.raises(ValueError) as caught:
        repository.create_closure("cl_secret", workspace_id, "pending", payload)

    assert _SECRET_CANARY not in str(caught.value)
    db_path = repository.database.path
    assert _SECRET_CANARY.encode() not in db_path.read_bytes()


def test_closure_create_rejects_duplicate_id(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_closure("cl_123", workspace_id, "pending", {"events": []})
