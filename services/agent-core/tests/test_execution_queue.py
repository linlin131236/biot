import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.task_closure import TaskTemplateId
from bolt_core.task_closure_service import TaskClosureService


def test_create_verification_command_item_does_not_execute():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")

    assert item.status == "pending"
    assert item.command == "pytest"
    assert not hasattr(queue, "execute")


def test_approve_does_not_execute_command():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")

    approved = queue.approve(item.id)

    assert approved.status == "approved"
    assert approved.result == ""


def test_reject_records_reason():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")

    rejected = queue.reject(item.id, "暂不处理")

    assert rejected.status == "rejected"
    assert rejected.reason == "暂不处理"


def test_mark_completed_records_result():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")

    completed = queue.mark_completed(item.id, "用户已处理")

    assert completed.status == "completed"
    assert completed.result == "用户已处理"


def test_workspace_write_pending_cannot_complete_directly():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "repair_suggestion", "处理修复建议", "需要修复", "workspace_write")

    with pytest.raises(ValueError):
        queue.mark_completed(item.id, "done")


def test_completed_item_cannot_be_approved():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.mark_completed(item.id, "用户已处理")

    with pytest.raises(ValueError):
        queue.approve(item.id)


def test_list_items_filters_by_closure_id():
    queue = ExecutionQueueService()
    queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.create_item("cl_2", "replan", "重新规划任务", "已停止", "read_only")

    items = queue.list_items("cl_1")

    assert len(items) == 1
    assert items[0].closure_id == "cl_1"


def test_unknown_item_raises():
    queue = ExecutionQueueService()

    with pytest.raises(ValueError):
        queue.get_item("missing")


def test_missing_evidence_with_command_creates_verification_command():
    closure_svc, closure = _bugfix_with_file_change_only()
    queue = ExecutionQueueService()

    items = closure_svc.propose_execution_items(closure.id, queue)

    assert items[0]["kind"] == "verification_command"
    assert items[0]["risk"] == "verification_command"
    assert items[0]["command"] == "pytest 或 pnpm test"
    assert items[0]["status"] == "pending"


def test_command_suggestion_only_records_queue_item():
    closure_svc, closure = _bugfix_with_file_change_only()
    queue = ExecutionQueueService()

    closure_svc.propose_execution_items(closure.id, queue)

    assert closure_svc.to_dict(closure.id)["commands"] == []


def test_waiting_permission_creates_workspace_write_manual_review():
    closure_svc = TaskClosureService()
    closure = closure_svc.start("修复拼写", TaskTemplateId.BUGFIX)
    closure_svc.mark_waiting_permission(closure.id, "perm_1")
    queue = ExecutionQueueService()

    items = closure_svc.propose_execution_items(closure.id, queue)

    assert items[0]["kind"] == "manual_review"
    assert items[0]["risk"] == "workspace_write"
    assert items[0]["title"] == "等待人工批准"


def test_stopped_creates_replan_item():
    closure_svc = TaskClosureService()
    closure = closure_svc.start("修复拼写", TaskTemplateId.BUGFIX)
    closure_svc.record_loop_status(closure.id, "max_steps_reached")
    queue = ExecutionQueueService()

    items = closure_svc.propose_execution_items(closure.id, queue)

    assert items[0]["kind"] == "replan"
    assert items[0]["risk"] == "read_only"
    assert items[0]["title"] == "重新规划任务"


def test_passed_assessment_creates_no_pending_items():
    closure_svc = TaskClosureService()
    closure = closure_svc.start("修复拼写", TaskTemplateId.BUGFIX)
    closure_svc.record_file_change(closure.id, "src/app.py")
    closure_svc.record_command(closure.id, "pytest", "12 passed")
    queue = ExecutionQueueService()

    items = closure_svc.propose_execution_items(closure.id, queue)

    assert items == []


def test_repeated_propose_does_not_duplicate_pending_items():
    closure_svc, closure = _bugfix_with_file_change_only()
    queue = ExecutionQueueService()

    first = closure_svc.propose_execution_items(closure.id, queue)
    second = closure_svc.propose_execution_items(closure.id, queue)

    assert first[0]["id"] == second[0]["id"]
    assert len(queue.list_items(closure.id)) == 1


def test_created_queue_item_restores_from_store(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")

    restored = ExecutionQueueService(store).get_item(item.id)

    assert restored.closure_id == "cl_1"
    assert restored.status == "pending"


def test_approved_queue_item_restores_from_store(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.approve(item.id)

    restored = ExecutionQueueService(store).get_item(item.id)

    assert restored.status == "approved"


def test_rejected_queue_item_restores_reason(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.reject(item.id, "暂不处理")

    restored = ExecutionQueueService(store).get_item(item.id)

    assert restored.status == "rejected"
    assert restored.reason == "暂不处理"


def test_completed_and_failed_queue_items_restore_results(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    completed = queue.create_item("cl_1", "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.mark_completed(completed.id, "用户已处理")
    failed = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(failed.id)
    queue.mark_failed(failed.id, "用户标记失败")

    restored = ExecutionQueueService(store)

    assert restored.get_item(completed.id).result == "用户已处理"
    assert restored.get_item(failed.id).status == "failed"
    assert restored.get_item(failed.id).result == "用户标记失败"


def test_pending_duplicate_semantics_survive_restore(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    first = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")

    restored = ExecutionQueueService(store)
    second = restored.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    restored.approve(first.id)
    third = restored.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")

    assert second.id == first.id
    assert third.id != first.id


def test_workspace_write_pending_restore_still_cannot_complete_directly(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "repair_suggestion", "处理修复建议", "需要修复", "workspace_write")
    restored = ExecutionQueueService(store)

    with pytest.raises(ValueError):
        restored.mark_completed(item.id, "done")


def _bugfix_with_file_change_only():
    closure_svc = TaskClosureService()
    closure = closure_svc.start("修复拼写", TaskTemplateId.BUGFIX)
    closure_svc.record_file_change(closure.id, "src/app.py")
    return closure_svc, closure
