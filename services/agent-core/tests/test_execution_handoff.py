import pytest

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
