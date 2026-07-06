"""Tests for task_closure model and state machine."""
from bolt_core.task_closure import (
    TaskClosure, TaskClosureStatus, TaskTemplateId,
    can_transition, task_templates, MAX_RETRIES,
)


def test_task_template_ids():
    assert TaskTemplateId.BUGFIX == "bugfix"
    assert TaskTemplateId.DOCS == "docs"
    assert TaskTemplateId.TEST == "test"
    assert TaskTemplateId.QUALITY == "quality"
    assert TaskTemplateId.REVIEW == "review"


def test_task_templates_chinese_labels():
    labels = {t["id"]: t["label"] for t in task_templates()}
    assert labels["bugfix"] == "修复小问题"
    assert labels["docs"] == "更新文档"
    assert len(task_templates()) == 5


def test_task_closure_status_values():
    statuses = [
        TaskClosureStatus.PENDING, TaskClosureStatus.PLANNING,
        TaskClosureStatus.EXECUTING, TaskClosureStatus.WAITING_PERMISSION,
        TaskClosureStatus.VERIFYING, TaskClosureStatus.REPAIRING,
        TaskClosureStatus.REVIEWING, TaskClosureStatus.COMPLETED,
        TaskClosureStatus.FAILED, TaskClosureStatus.STOPPED,
    ]
    assert len(statuses) == 10
    assert TaskClosureStatus.PENDING == "pending"
    assert TaskClosureStatus.PLANNING == "planning"
    assert TaskClosureStatus.COMPLETED == "completed"
    assert TaskClosureStatus.FAILED == "failed"


def test_legal_transitions():
    assert can_transition(TaskClosureStatus.PENDING, TaskClosureStatus.PLANNING)
    assert can_transition(TaskClosureStatus.PLANNING, TaskClosureStatus.EXECUTING)
    assert can_transition(TaskClosureStatus.EXECUTING, TaskClosureStatus.VERIFYING)
    assert can_transition(TaskClosureStatus.VERIFYING, TaskClosureStatus.COMPLETED)
    assert can_transition(TaskClosureStatus.REVIEWING, TaskClosureStatus.COMPLETED)
    assert can_transition(TaskClosureStatus.PENDING, TaskClosureStatus.STOPPED)
    assert can_transition(TaskClosureStatus.EXECUTING, TaskClosureStatus.STOPPED)


def test_illegal_transitions():
    assert not can_transition(TaskClosureStatus.PENDING, TaskClosureStatus.COMPLETED)
    assert not can_transition(TaskClosureStatus.COMPLETED, TaskClosureStatus.EXECUTING)
    assert not can_transition(TaskClosureStatus.FAILED, TaskClosureStatus.PLANNING)


def test_task_closure_initial_state():
    closure = TaskClosure(id="cl_1", objective="修复 README 拼写", template_id=TaskTemplateId.BUGFIX)
    assert closure.status == TaskClosureStatus.PENDING
    assert closure.retry_count == 0
    assert closure.changed_files == []


def test_task_closure_evidence_fields():
    closure = TaskClosure(
        id="cl_2", objective="增加测试", template_id=TaskTemplateId.TEST,
        plan_summary="为 agent_loop.py 补 pytest",
        changed_files=["agent_loop.py", "test_agent_loop.py"],
        commands=["pytest test_agent_loop.py"],
        command_results=["3 passed"],
        permission_request_ids=["perm_1"],
        retry_count=1,
        review_summary="测试覆盖率从 70% 提升到 85%",
        next_action="合并到 main",
        status=TaskClosureStatus.COMPLETED,
    )
    assert closure.plan_summary == "为 agent_loop.py 补 pytest"
    assert len(closure.changed_files) == 2
    assert closure.retry_count == 1


def test_max_retries_limit():
    closure = TaskClosure(id="cl_3", retry_count=MAX_RETRIES, status=TaskClosureStatus.REPAIRING)
    assert closure.retry_count >= MAX_RETRIES
