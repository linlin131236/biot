"""Tests for SubtaskAssignmentService."""
import pytest
from bolt_core.subtask_assignment import (
    SubtaskAssignmentService, SubtaskStatus, RiskLevel,
)


def test_create_builder_task():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("实现登录", "描述", "builder", "build", risk_level="low")
    assert r.task_id.startswith("task-")
    assert r.assigned_role == "builder"
    assert r.status == SubtaskStatus.PENDING


def test_create_researcher_task():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("调研", "描述", "researcher", "research", risk_level="low")
    assert r.assigned_role == "researcher"


def test_researcher_cannot_build():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("写代码", "描述", "researcher", "build", risk_level="low")
    assert r.valid is False
    assert r.blocked is True


def test_reviewer_cannot_build():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("写代码", "描述", "reviewer", "build", risk_level="low")
    assert r.valid is False


def test_invalid_role():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("t", "d", "invalid", "build")
    assert r.valid is False


def test_high_risk_requires_human():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("危险任务", "d", "builder", "build", risk_level="high")
    assert r.requires_human_confirmation is True


def test_critical_risk_requires_human():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("严重任务", "d", "builder", "build", risk_level="critical")
    assert r.requires_human_confirmation is True


def test_low_risk_no_human():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("低风险", "d", "builder", "build", risk_level="low")
    assert r.requires_human_confirmation is False


def test_list_assignments():
    svc = SubtaskAssignmentService()
    svc.create_assignment("a", "d", "builder", "build", risk_level="low")
    svc.create_assignment("b", "d", "researcher", "research", risk_level="low")
    assert len(svc.list_assignments()) == 2


def test_list_by_role():
    svc = SubtaskAssignmentService()
    svc.create_assignment("a", "d", "builder", "build", risk_level="low")
    svc.create_assignment("b", "d", "researcher", "research", risk_level="low")
    assert len(svc.list_assignments(role="builder")) == 1


def test_board_summary():
    svc = SubtaskAssignmentService()
    svc.create_assignment("a", "d", "builder", "build", risk_level="low")
    summary = svc.board_summary_cn()
    assert summary["total_tasks"] == 1
    assert "by_status" in summary


def test_update_status():
    svc = SubtaskAssignmentService()
    r = svc.create_assignment("任务", "d", "builder", "build", risk_level="low")
    result = svc.update_status(r.task_id, "in_progress")
    assert result.valid is True


def test_update_status_dependency_block():
    svc = SubtaskAssignmentService()
    r1 = svc.create_assignment("依赖任务", "d", "researcher", "research", risk_level="low")
    r2 = svc.create_assignment("主任务", "d", "builder", "build", dependencies=[r1.task_id], risk_level="low")
    # Cannot go to ready if dependency not completed
    result = svc.update_status(r2.task_id, "ready")
    assert result.valid is False


def test_update_status_dependency_ok():
    svc = SubtaskAssignmentService()
    r1 = svc.create_assignment("依赖任务", "d", "researcher", "research", risk_level="low")
    svc.update_status(r1.task_id, "completed")
    r2 = svc.create_assignment("主任务", "d", "builder", "build", dependencies=[r1.task_id], risk_level="low")
    result = svc.update_status(r2.task_id, "ready")
    assert result.valid is True


def test_status_labels_chinese():
    assert SubtaskStatus.PENDING.label_cn == "待办"
    assert SubtaskStatus.BLOCKED.label_cn == "阻塞"
    assert SubtaskStatus.COMPLETED.label_cn == "已完成"


def test_risk_labels_chinese():
    assert RiskLevel.HIGH.label_cn == "高"
    assert RiskLevel.CRITICAL.label_cn == "严重"
