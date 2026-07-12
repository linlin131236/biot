import json

from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository


def _repository(root):
    return ControlPlaneRepository(Database.open(root))


def test_handoff_service_uses_repository_and_recovers_without_legacy_json(tmp_path):
    root = tmp_path / "user-data"
    legacy = tmp_path / "workspace" / ".bolt" / "execution-audit.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"version": 1, "queue_items": [], "handoff_records": [], "closure_records": []}), encoding="utf-8")
    repository = _repository(root)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_closure("cl_123", workspace_id, "pending", {"events": []})
    queue = ExecutionQueueService(repository=repository, workspace_id=workspace_id)
    item = queue.create_item("cl_123", "manual_review", "Review", "Review", "read_only")
    item = queue.approve(item.id)

    service = ExecutionHandoffService(repository=repository, workspace_id=workspace_id)
    record = service.create_from_queue_item(item)
    rebuilt = ExecutionHandoffService(repository=_repository(root), workspace_id=workspace_id)

    assert rebuilt.get_record(record.id).queue_item_id == item.id
    assert json.loads(legacy.read_text(encoding="utf-8"))["handoff_records"] == []
