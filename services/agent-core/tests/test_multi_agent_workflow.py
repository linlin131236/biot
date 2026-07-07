"""Tests for MultiAgentWorkflowService."""
import pytest

from bolt_core.multi_agent_workflow import (
    MultiAgentWorkflowService,
    MultiAgentWorkflow,
    WorkflowState,
    PlannerOutput,
    BuilderOutput,
    ReviewerOutput,
    TransitionResult,
    _VALID_TRANSITIONS,
)


# ── WorkflowState enum ──────────────────────────────────────────────────

def test_state_labels_chinese():
    assert WorkflowState.PLANNING.label_cn == "规划中"
    assert WorkflowState.BUILDING.label_cn == "构建中"
    assert WorkflowState.REVIEWING.label_cn == "审查中"
    assert WorkflowState.APPROVED.label_cn == "已批准"
    assert WorkflowState.CHANGES_REQUESTED.label_cn == "需修改"
    assert WorkflowState.BLOCKED.label_cn == "已阻塞"
    assert WorkflowState.FAILED.label_cn == "已失败"


def test_valid_transitions_planning():
    valid = _VALID_TRANSITIONS[WorkflowState.PLANNING]
    assert WorkflowState.READY_FOR_BUILD in valid
    assert WorkflowState.FAILED in valid
    assert WorkflowState.BLOCKED in valid
    assert WorkflowState.APPROVED not in valid  # cannot skip to approved


def test_valid_transitions_reviewing():
    valid = _VALID_TRANSITIONS[WorkflowState.REVIEWING]
    assert WorkflowState.APPROVED in valid
    assert WorkflowState.CHANGES_REQUESTED in valid
    assert WorkflowState.BLOCKED in valid
    assert WorkflowState.FAILED in valid


def test_terminal_states():
    assert _VALID_TRANSITIONS[WorkflowState.APPROVED] == []
    assert _VALID_TRANSITIONS[WorkflowState.FAILED] == []


# ── Data models ─────────────────────────────────────────────────────────

def test_planner_output_to_dict():
    po = PlannerOutput(
        task_breakdown=[{"title": "t1", "desc": "d1"}],
        risk_assessment="low",
        assignment={"t1": "builder"},
        source_refs=["docs/spec.md"],
        submitted_at="2026-07-07T00:00:00Z",
        submitted_by_context="ctx-planner-1",
    )
    d = po.to_dict()
    assert d["task_breakdown"] == [{"title": "t1", "desc": "d1"}]
    assert d["risk_assessment"] == "low"
    assert d["source_refs"] == ["docs/spec.md"]


def test_builder_output_to_dict():
    bo = BuilderOutput(
        code_changes="added login",
        tests="all passed",
        evidence_refs=["test.log"],
        source_refs=["docs/spec.md"],
        submitted_by_context="ctx-builder-1",
    )
    d = bo.to_dict()
    assert d["code_changes"] == "added login"
    assert d["evidence_refs"] == ["test.log"]


def test_reviewer_output_to_dict():
    ro = ReviewerOutput(
        findings=[],
        evidence=["code:10"],
        tests_status="passed",
        residual_risks=[],
        verdict="approved",
        source_refs=["docs/review.md"],
        submitted_by_context="ctx-reviewer-1",
    )
    d = ro.to_dict()
    assert d["verdict"] == "approved"
    assert d["evidence"] == ["code:10"]


# ── Service: create_workflow ────────────────────────────────────────────

def test_create_workflow():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("测试工作流")
    assert wf.workflow_id.startswith("wf-")
    assert wf.title_cn == "测试工作流"
    assert wf.state == WorkflowState.PLANNING
    assert wf.created_at
    assert len(wf.state_history) == 1


def test_create_workflow_unique_ids():
    svc = MultiAgentWorkflowService()
    wf1 = svc.create_workflow("a")
    wf2 = svc.create_workflow("b")
    assert wf1.workflow_id != wf2.workflow_id


# ── Service: list/get ───────────────────────────────────────────────────

def test_list_workflows():
    svc = MultiAgentWorkflowService()
    svc.create_workflow("a")
    svc.create_workflow("b")
    workflows = svc.list_workflows()
    assert len(workflows) == 2


def test_get_workflow_found():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("test")
    found = svc.get_workflow(wf.workflow_id)
    assert found is not None
    assert found.workflow_id == wf.workflow_id


def test_get_workflow_not_found():
    svc = MultiAgentWorkflowService()
    assert svc.get_workflow("nonexistent") is None


# ── Service: status_summary_cn ──────────────────────────────────────────

def test_status_summary_planning():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("test")
    summary = svc.status_summary_cn(wf.workflow_id)
    assert "规划" in summary["summary_cn"]
    assert summary["state"] == "planning"


def test_status_summary_approved():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("test")
    # Fast-forward to approved via internal transition
    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(svc._workflows[wf.workflow_id], WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests ok", ["ev"], ["ref"], "ctx-b")
    svc.assign_reviewer_output(wf.workflow_id, [], ["ev"], "passed", [], "approved", ["ref"], "ctx-r")
    summary = svc.status_summary_cn(wf.workflow_id)
    assert summary["state"] == "approved"


def test_status_summary_not_found():
    svc = MultiAgentWorkflowService()
    result = svc.status_summary_cn("nonexistent")
    assert "error" in result


# ── Happy path: planning → approved ─────────────────────────────────────

def test_happy_path():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("完整测试")

    # Step 1: Planner submits
    r1 = svc.assign_planner_output(
        wf.workflow_id,
        [{"title": "登录", "desc": "实现登录"}],
        "low",
        {"登录": "builder"},
        ["docs/spec.md"],
        "ctx-planner",
    )
    assert r1.valid
    assert wf.state == WorkflowState.READY_FOR_BUILD

    # Step 2: Builder starts (manual transition via internal _transition)
    svc._transition(wf, WorkflowState.BUILDING, "构建者开始")

    # Step 3: Builder submits
    r2 = svc.assign_builder_output(
        wf.workflow_id,
        "实现登录功能",
        "tests pass",
        ["test.log"],
        ["docs/spec.md"],
        "ctx-builder",
    )
    assert r2.valid
    assert wf.state == WorkflowState.READY_FOR_REVIEW

    # Step 4: Reviewer submits (different context)
    r3 = svc.assign_reviewer_output(
        wf.workflow_id,
        [],
        ["code:10"],
        "passed",
        [],
        "approved",
        ["docs/review.md"],
        "ctx-reviewer",
    )
    assert r3.valid
    assert wf.state == WorkflowState.APPROVED


# ── Builder cannot self-approve ─────────────────────────────────────────

def test_builder_self_approval_blocked():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("自我批准测试")

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-same")

    # Reviewer submits with SAME context as builder → blocked
    result = svc.assign_reviewer_output(
        wf.workflow_id, [], ["ev"], "passed", [], "approved", ["ref"],
        "ctx-same",  # same as builder!
    )
    assert result.valid is False
    assert result.blocked is True
    assert "自我批准" in result.message_cn or "不能与构建者" in result.message_cn


# ── Reviewer must have evidence ─────────────────────────────────────────

def test_reviewer_no_evidence_blocked():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("缺证据测试")

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")

    result = svc.assign_reviewer_output(
        wf.workflow_id, [], [], "passed", [], "approved", [],  # no evidence, no source_refs
        "ctx-r",
    )
    assert result.valid is False


# ── P1/P2 cannot be approved ────────────────────────────────────────────

def test_p1_block_approval():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("P1阻塞测试")

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")

    result = svc.assign_reviewer_output(
        wf.workflow_id,
        [{"severity": "P1", "desc": "安全漏洞", "location": "auth.py:10"}],
        ["auth.py:10"],
        "failed",
        ["安全风险"],
        "approved",  # trying to approve with P1!
        ["ref"],
        "ctx-r",
    )
    assert result.valid is False
    assert "P1" in result.message_cn or "P2" in result.message_cn


# ── changes_requested → back to building ────────────────────────────────

def test_changes_requested_cycle():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("修改循环测试")

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")

    # Reviewer requests changes
    r1 = svc.assign_reviewer_output(
        wf.workflow_id,
        [{"severity": "P3", "desc": "可以改进"}],
        ["code:20"],
        "passed",
        [],
        "changes_requested",
        ["ref"],
        "ctx-r",
    )
    assert r1.valid
    assert wf.state == WorkflowState.CHANGES_REQUESTED

    # Builder fixes and resubmits
    r2 = svc.assign_builder_output(wf.workflow_id, "fixed code", "tests pass", ["ev2"], ["ref2"], "ctx-b")
    assert r2.valid
    assert wf.state == WorkflowState.READY_FOR_REVIEW


# ── Invalid transitions ─────────────────────────────────────────────────

def test_builder_cannot_go_directly_to_approved():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("越权测试")
    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")

    result = svc.validate_transition(wf.workflow_id, "approved")
    assert result.valid is False
    assert result.blocked is True


def test_planner_cannot_skip_to_approved():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("跳跃测试")
    result = svc.validate_transition(wf.workflow_id, "approved")
    assert result.valid is False


def test_validate_transition_invalid_state():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("test")
    result = svc.validate_transition(wf.workflow_id, "invalid_state")
    assert result.valid is False


# ── State history ───────────────────────────────────────────────────────

def test_state_history_tracks_all_transitions():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("历史测试")
    assert len(wf.state_history) == 1  # creation

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    assert len(wf.state_history) == 2


# ── Workflow to_dict ────────────────────────────────────────────────────

def test_workflow_to_dict():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("dict测试")
    d = wf.to_dict()
    assert d["workflow_id"] == wf.workflow_id
    assert d["state"] == "planning"
    assert d["state_label_cn"] == "规划中"
    assert d["planner_output"] is None


# ── blocked state ───────────────────────────────────────────────────────

def test_reviewer_can_block():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("阻塞测试")

    svc.assign_planner_output(wf.workflow_id, [{"t": "t1"}], "low", {"t1": "builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")

    result = svc.assign_reviewer_output(
        wf.workflow_id,
        [{"severity": "P1", "desc": "严重安全漏洞"}],
        ["code:1"],
        "failed",
        ["高风险"],
        "blocked",
        ["ref"],
        "ctx-r",
    )
    assert result.valid
    assert wf.state == WorkflowState.BLOCKED
    assert wf.blocked_reason_cn
