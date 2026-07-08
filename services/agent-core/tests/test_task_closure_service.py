"""Tests for TaskClosureService: evidence recording, no execution."""
import time
from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.task_closure import (
    TaskClosure, TaskClosureStatus, TaskTemplateId, MAX_RETRIES, can_transition,
)


def test_service_bind_run_and_find_by_run():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    svc.bind_run(closure.id, "run_43")

    found = svc.find_by_run("run_43")
    assert found is not None
    assert found.id == closure.id


def test_service_bind_goal_and_find_by_goal():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    svc.bind_goal(closure.id, "goal_43")

    found = svc.find_by_goal("goal_43")
    assert found is not None
    assert found.id == closure.id


def test_service_record_loop_status_waiting_permission():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    updated = svc.record_loop_status(closure.id, "pending_permission")

    assert updated.status == TaskClosureStatus.WAITING_PERMISSION


def test_service_record_loop_status_max_steps_stopped():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    updated = svc.record_loop_status(closure.id, "max_steps_reached")

    assert updated.status == TaskClosureStatus.STOPPED


def test_service_mark_completed_sets_final_status():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    svc.mark_completed(closure.id, "全部通过")
    data = svc.to_dict(closure.id)

    assert data["status"] == TaskClosureStatus.COMPLETED
    assert data["final_status"] == TaskClosureStatus.COMPLETED


def test_service_record_tool_result_only_records():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    updated = svc.record_tool_result(closure.id, {"request_id": "tool_43", "status": "executed", "output": "读取完成"})

    assert updated.commands == ["tool:tool_43"]
    assert updated.command_results == ["读取完成"]
    assert not hasattr(svc, "approve_permission")


def test_service_mark_unknown_closure_raises():
    svc = TaskClosureService()

    try:
        svc.mark_completed("missing", "完成")
        assert False
    except ValueError as exc:
        assert "not found" in str(exc)


def test_service_start_creates_closure():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    assert closure.id.startswith("cl_")
    assert closure.objective == "修复拼写"
    assert closure.template_id == TaskTemplateId.BUGFIX
    assert closure.status == TaskClosureStatus.PENDING
    assert closure.run_id is None
    assert closure.retry_count == 0


def test_service_transition_legal():
    svc = TaskClosureService()
    closure = svc.start("增加测试", TaskTemplateId.TEST)
    transitioned = svc.transition(closure.id, TaskClosureStatus.PLANNING)
    assert transitioned.status == TaskClosureStatus.PLANNING
    executing = svc.transition(closure.id, TaskClosureStatus.EXECUTING)
    assert executing.status == TaskClosureStatus.EXECUTING


def test_service_transition_records_previous_status():
    svc = TaskClosureService()
    closure = svc.start("增加测试", TaskTemplateId.TEST)
    svc.transition(closure.id, TaskClosureStatus.PLANNING)

    record = svc._store[closure.id]
    assert record.events[-1]["from"] == TaskClosureStatus.PENDING
    assert record.events[-1]["to"] == TaskClosureStatus.PLANNING


def test_service_to_dict_exposes_final_status():
    svc = TaskClosureService()
    closure = svc.start("增加测试", TaskTemplateId.TEST)
    data = svc.to_dict(closure.id)

    assert data["status"] == TaskClosureStatus.PENDING
    assert data["final_status"] == TaskClosureStatus.PENDING


def test_service_transition_illegal_raises():
    svc = TaskClosureService()
    closure = svc.start("增加测试", TaskTemplateId.TEST)
    # pending → completed (skip planning/executing)
    try:
        svc.transition(closure.id, TaskClosureStatus.COMPLETED)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "illegal transition" in str(e).lower()


def test_service_record_command():
    svc = TaskClosureService()
    closure = svc.start("跑质量门", TaskTemplateId.QUALITY)
    svc.transition(closure.id, TaskClosureStatus.PLANNING)
    svc.transition(closure.id, TaskClosureStatus.EXECUTING)
    svc.record_command(closure.id, "pnpm quality", "140 passed, 0 failed")
    result = svc.to_dict(closure.id)
    assert result["commands"] == ["pnpm quality"]
    assert result["command_results"] == ["140 passed, 0 failed"]


def test_service_restores_closure_evidence_from_audit_store(tmp_path):
    store = ExecutionAuditStore(tmp_path / "execution-audit.json")
    first = TaskClosureService(store)
    closure = first.start("修复拼写", TaskTemplateId.BUGFIX, run_id="run_1")
    first.record_file_change(closure.id, "src/app.py")
    first.record_command(closure.id, "pytest", "12 passed")

    restored = TaskClosureService(store)
    data = restored.to_dict(closure.id)

    assert data["run_id"] == "run_1"
    assert data["changed_files"] == ["src/app.py"]
    assert data["commands"] == ["pytest"]
    assert data["command_results"] == ["12 passed"]


def test_service_record_file_change():
    svc = TaskClosureService()
    closure = svc.start("修复小问题", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/App.tsx")
    result = svc.to_dict(closure.id)
    assert "src/App.tsx" in result["changed_files"]


def test_service_record_permission():
    svc = TaskClosureService()
    closure = svc.start("修复小问题", TaskTemplateId.BUGFIX)
    svc.record_permission(closure.id, "perm_1")
    result = svc.to_dict(closure.id)
    assert "perm_1" in result["permission_request_ids"]


def test_service_record_review():
    svc = TaskClosureService()
    closure = svc.start("生成审查摘要", TaskTemplateId.REVIEW)
    svc.transition(closure.id, TaskClosureStatus.PLANNING)
    svc.transition(closure.id, TaskClosureStatus.EXECUTING)
    svc.transition(closure.id, TaskClosureStatus.VERIFYING)
    svc.transition(closure.id, TaskClosureStatus.REVIEWING)
    reviewed = svc.record_review(closure.id, "全部通过", True)
    assert reviewed.review_summary == "全部通过"
    assert reviewed.next_action == "合并到 main"


def test_service_should_stop_repairing():
    svc = TaskClosureService()
    closure = svc.start("修复小问题", TaskTemplateId.BUGFIX)
    for i in range(MAX_RETRIES):
        svc.increment_retry(closure.id)
    assert svc.should_stop_repairing(closure.id)


def test_service_should_not_stop_before_limit():
    svc = TaskClosureService()
    closure = svc.start("修复小问题", TaskTemplateId.BUGFIX)
    svc.increment_retry(closure.id)  # 1 retry
    assert not svc.should_stop_repairing(closure.id)


def test_service_unknown_closure_raises():
    svc = TaskClosureService()
    try:
        svc.transition("unknown_id", TaskClosureStatus.PLANNING)
        assert False
    except ValueError:
        pass


def test_service_list_closures():
    svc = TaskClosureService()
    c1 = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    c2 = svc.start("更新文档", TaskTemplateId.DOCS)
    closures = svc.list_closures()
    assert len(closures) == 2
    ids = [c["id"] for c in closures]
    assert c1.id in ids and c2.id in ids


def test_service_does_not_execute_tools():
    """TaskClosureService must never execute tools, push, release, or approve permissions."""
    svc = TaskClosureService()
    closure = svc.start("增加测试", TaskTemplateId.TEST)
    # Service has no execute/push/release/approve methods
    assert not hasattr(svc, "execute_tool")
    assert not hasattr(svc, "push")
    assert not hasattr(svc, "release")
    assert not hasattr(svc, "approve_permission")


def test_service_assess_completion_missing_does_not_complete():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")

    assessment = svc.assess_completion(closure.id)
    updated = svc.update_assessment(closure.id)

    assert assessment["status"] == "missing_evidence"
    assert updated.status != TaskClosureStatus.COMPLETED
    assert updated.next_action == "缺少验证证据"


def test_service_waiting_permission_not_completed_by_assessment():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.mark_waiting_permission(closure.id, "perm_44")

    updated = svc.update_assessment(closure.id)

    assert updated.status == TaskClosureStatus.WAITING_PERMISSION
    assert updated.next_action == "等待人工批准"


def test_service_stopped_not_completed_by_assessment():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_loop_status(closure.id, "max_steps_reached")

    updated = svc.update_assessment(closure.id)

    assert updated.status == TaskClosureStatus.STOPPED
    assert updated.next_action == "已达到最大步数，需要重新规划或人工处理"


def test_service_passed_assessment_completes():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")
    svc.record_command(closure.id, "pytest", "12 passed")

    updated = svc.update_assessment(closure.id)

    assert updated.status == TaskClosureStatus.COMPLETED
    assert updated.next_action == "已完成"


def test_service_failed_assessment_sets_repair_suggestion():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.mark_failed(closure.id, "pytest failed")

    updated = svc.update_assessment(closure.id)

    assert updated.status == TaskClosureStatus.FAILED
    assert updated.next_action == "根据失败输出修复问题后重新记录验证证据"


def test_result_summary_completed():
    svc = TaskClosureService()
    closure = svc.start("增加登录功能", TaskTemplateId.BUGFIX)
    svc.transition(closure.id, TaskClosureStatus.PLANNING)
    svc.transition(closure.id, TaskClosureStatus.EXECUTING)
    svc.record_file_change(closure.id, "src/auth.py")
    svc.record_file_change(closure.id, "src/auth.test.ts")
    svc.record_command(closure.id, "pytest", "16 passed")
    svc.record_command(closure.id, "pnpm quality", "OK")
    import time as _time
    _time.sleep(0.05)
    svc.mark_completed(closure.id, "全部通过")

    summary = svc.result_summary(closure.id)
    assert summary["closure_id"] == closure.id
    assert summary["status"] == TaskClosureStatus.COMPLETED
    assert summary["duration_seconds"] > 0
    assert "src/auth.py" in summary["changed_files"]
    assert "pytest" in summary["commands"]
    assert len(summary["command_results"]) <= 5
    assert summary["review_summary"] == "全部通过"
    assert summary["next_action"] == "已完成"
    assert summary["retry_count"] == 0


def test_result_summary_failed():
    svc = TaskClosureService()
    closure = svc.start("修复崩溃", TaskTemplateId.BUGFIX)
    svc.record_tool_result(closure.id, {"request_id": "tool_1", "status": "failed", "output": "Segmentation fault"})
    svc.mark_failed(closure.id, "工具执行失败")

    summary = svc.result_summary(closure.id)
    assert summary["status"] == TaskClosureStatus.FAILED
    assert summary["error"] is None  # mark_failed doesn't set error field
    assert summary["retry_count"] == 0


def test_result_summary_empty_closure():
    svc = TaskClosureService()
    closure = svc.start("空任务", TaskTemplateId.DOCS)

    summary = svc.result_summary(closure.id)
    assert summary["closure_id"] == closure.id
    assert summary["status"] == TaskClosureStatus.PENDING
    assert summary["duration_seconds"] == 0
    assert summary["changed_files"] == []
    assert summary["commands"] == []
    assert summary["command_results"] == []
    assert summary["final_output"] is None
    assert summary["error"] is None
    assert summary["review_summary"] is None
    assert summary["next_action"] is None
    assert summary["retry_count"] == 0
    assert summary["permission_requests"] == []
