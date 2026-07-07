"""Tests for MultiAgentWorkflowService — gates, self-approval, transitions."""
from bolt_core.multi_agent_workflow import MultiAgentWorkflowService, WorkflowState


def test_builder_self_approval_blocked():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("自我批准测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-same")
    result = svc.assign_reviewer_output(wf.workflow_id, [], ["ev"], "passed", [], "approved", ["ref"], "ctx-same")
    assert result.valid is False
    assert result.blocked is True


def test_reviewer_no_evidence_blocked():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("缺证据测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")
    result = svc.assign_reviewer_output(wf.workflow_id, [], [], "passed", [], "approved", [], "ctx-r")
    assert result.valid is False


def test_p1_block_approval():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("P1阻塞测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")
    result = svc.assign_reviewer_output(wf.workflow_id, [{"severity":"P1","desc":"漏洞"}], ["ev"], "failed", ["风险"], "approved", ["ref"], "ctx-r")
    assert result.valid is False


def test_changes_requested_cycle():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("修改循环测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")
    r1 = svc.assign_reviewer_output(wf.workflow_id, [{"severity":"P3","desc":"改进"}], ["code:20"], "passed", [], "changes_requested", ["ref"], "ctx-r")
    assert r1.valid
    assert wf.state == WorkflowState.CHANGES_REQUESTED
    r2 = svc.assign_builder_output(wf.workflow_id, "fixed", "tests pass", ["ev2"], ["ref2"], "ctx-b")
    assert r2.valid
    assert wf.state == WorkflowState.READY_FOR_REVIEW


def test_builder_cannot_go_directly_to_approved():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("越权测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    result = svc.validate_transition(wf.workflow_id, "approved")
    assert result.valid is False


def test_planner_cannot_skip_to_approved():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("跳跃测试")
    result = svc.validate_transition(wf.workflow_id, "approved")
    assert result.valid is False


def test_state_history_tracks_all_transitions():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("历史测试")
    assert len(wf.state_history) == 1
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    assert len(wf.state_history) == 2


def test_reviewer_can_block():
    svc = MultiAgentWorkflowService()
    wf = svc.create_workflow("阻塞测试")
    svc.assign_planner_output(wf.workflow_id, [{"t":"t1"}], "low", {"t1":"builder"}, ["refs"], "ctx-p")
    svc._transition(wf, WorkflowState.BUILDING, "")
    svc.assign_builder_output(wf.workflow_id, "code", "tests", ["ev"], ["ref"], "ctx-b")
    result = svc.assign_reviewer_output(wf.workflow_id, [{"severity":"P1","desc":"漏洞"}], ["code:1"], "failed", ["高风险"], "blocked", ["ref"], "ctx-r")
    assert result.valid
    assert wf.state == WorkflowState.BLOCKED
    assert wf.blocked_reason_cn
