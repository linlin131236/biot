import json

import pytest

from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository


def _repository(root):
    return ControlPlaneRepository(Database.open(root))


def _seed(repository, workspace_path="C:/Projects/A"):
    workspace_id = repository.save_workspace(workspace_path)
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})
    return workspace_id


def test_queue_service_uses_repository_and_recovers_without_legacy_json(tmp_path):
    root = tmp_path / "user-data"
    legacy = tmp_path / "workspace" / ".bolt" / "execution-audit.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"version": 1, "queue_items": [], "handoff_records": [], "closure_records": []}), encoding="utf-8")
    repository = _repository(root)
    workspace_id = _seed(repository)

    service = ExecutionQueueService(repository=repository, workspace_id=workspace_id)
    item = service.create_item("cl_123", "manual_review", "Review", "Review", "read_only")

    rebuilt = ExecutionQueueService(repository=_repository(root), workspace_id=workspace_id)

    assert rebuilt.get_item(item.id).title == "Review"
    assert json.loads(legacy.read_text(encoding="utf-8"))["queue_items"] == []


def test_queue_service_repository_rejects_secret_without_falling_back(tmp_path):
    repository = _repository(tmp_path / "user-data")
    workspace_id = _seed(repository)
    service = ExecutionQueueService(repository=repository, workspace_id=workspace_id)

    with pytest.raises(ValueError):
        service.create_item("cl_123", "manual_review", "Bearer ghp_secretcanary123456789", "Review", "read_only")

    assert repository.list_queue_items(workspace_id) == []
