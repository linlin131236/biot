import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_handoff import ExecutionHandoffInvalidTransition, ExecutionHandoffNotFound, ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueService


def test_verification_command_creates_manual_verification_without_execution():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()

    record = handoffs.create_from_queue_item(item)

    assert record.handoff_type == "manual_verification"
    assert record.command == "pytest"
    assert not hasattr(handoffs, "execute")


def test_waiting_permission_creates_permission_panel():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "manual_review", "等待人工批准", "等待人工批准", "workspace_write")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()

    record = handoffs.create_from_queue_item(item)

    assert record.handoff_type == "permission_panel"
    assert record.status == "waiting_permission"
    assert record.instruction == "请到权限面板处理原始权限请求"


def test_repair_suggestion_creates_goal_input():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "repair_suggestion", "处理修复建议", "修复失败测试", "workspace_write")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()

    record = handoffs.create_from_queue_item(item)

    assert record.handoff_type == "goal_input"
    assert record.goal_objective == "修复失败测试"


def test_unknown_handoff_id_raises():
    handoffs = ExecutionHandoffService()

    with pytest.raises(ExecutionHandoffNotFound):
        handoffs.get_record("missing")


def test_complete_and_fail_only_update_handoff_record():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    completed_record = handoffs.create_from_queue_item(item)

    completed = handoffs.complete(completed_record.id, "用户已运行")

    assert completed.queue_item_id == item.id
    assert completed.status == "completed"
    assert item.status == "approved"


def test_completed_handoff_cannot_be_failed():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    handoffs.complete(record.id, "用户已运行")

    with pytest.raises(ExecutionHandoffInvalidTransition):
        handoffs.fail(record.id, "用户标记失败")


def test_failed_handoff_cannot_be_completed():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    handoffs.fail(record.id, "用户标记失败")

    with pytest.raises(ExecutionHandoffInvalidTransition):
        handoffs.complete(record.id, "用户已运行")


def test_same_queue_item_does_not_create_duplicate_handoff():
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "replan", "重新规划任务", "已停止", "read_only")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()

    first = handoffs.create_from_queue_item(item)
    second = handoffs.create_from_queue_item(item)

    assert first.id == second.id
    assert len(handoffs.list_records("cl_1")) == 1


def test_approved_queue_item_handoff_restores_from_store(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(item)

    restored = ExecutionHandoffService(store).get_record(record.id)

    assert restored.queue_item_id == item.id
    assert restored.status == "ready_for_manual_action"


def test_same_queue_item_after_restore_does_not_duplicate_handoff(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    first = ExecutionHandoffService(store).create_from_queue_item(item)

    restored_queue_item = ExecutionQueueService(store).get_item(item.id)
    second = ExecutionHandoffService(store).create_from_queue_item(restored_queue_item)

    assert second.id == first.id


def test_completed_handoff_restores_terminal_status(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(item)
    handoffs.complete(record.id, "用户已运行")

    restored = ExecutionHandoffService(store).get_record(record.id)

    assert restored.status == "completed"
    assert restored.result == "用户已运行"


def test_failed_handoff_restores_terminal_status(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(item)
    handoffs.fail(record.id, "用户标记失败")

    restored = ExecutionHandoffService(store).get_record(record.id)

    assert restored.status == "failed"
    assert restored.result == "用户标记失败"


def test_restored_terminal_handoffs_cannot_be_rewritten(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    completed_item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    failed_item = queue.create_item("cl_2", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(completed_item.id)
    queue.approve(failed_item.id)
    handoffs = ExecutionHandoffService(store)
    completed = handoffs.create_from_queue_item(completed_item)
    failed = handoffs.create_from_queue_item(failed_item)
    handoffs.complete(completed.id, "用户已运行")
    handoffs.fail(failed.id, "用户标记失败")
    restored = ExecutionHandoffService(store)

    with pytest.raises(ExecutionHandoffInvalidTransition):
        restored.fail(completed.id, "改写失败")
    with pytest.raises(ExecutionHandoffInvalidTransition):
        restored.complete(failed.id, "改写完成")


def test_complete_and_fail_after_restore_do_not_update_queue_item(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    queue = ExecutionQueueService(store)
    completed_item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    failed_item = queue.create_item("cl_2", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(completed_item.id)
    queue.approve(failed_item.id)
    handoffs = ExecutionHandoffService(store)
    completed = handoffs.create_from_queue_item(completed_item)
    failed = handoffs.create_from_queue_item(failed_item)
    restored_handoffs = ExecutionHandoffService(store)
    restored_handoffs.complete(completed.id, "用户已运行")
    restored_handoffs.fail(failed.id, "用户标记失败")
    restored_queue = ExecutionQueueService(store)

    assert restored_queue.get_item(completed_item.id).status == "approved"
    assert restored_queue.get_item(failed_item.id).status == "approved"
