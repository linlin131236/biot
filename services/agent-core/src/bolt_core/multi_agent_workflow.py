"""Multi-Agent Workflow Service. Manages Planner→Builder→Reviewer pipeline
with strict transition validation. Pure state machine; no execution.

Data models and state definitions live in multi_agent_workflow_models.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from bolt_core.multi_agent_workflow_models import (
    WorkflowState, PlannerOutput, BuilderOutput, ReviewerOutput,
    MultiAgentWorkflow, TransitionResult,
    _VALID_TRANSITIONS, _STATE_SUMMARIES_CN,
)


class MultiAgentWorkflowService:
    """Manages multi-agent workflows. Pure state machine; no execution."""

    def __init__(self) -> None:
        self._workflows: dict[str, MultiAgentWorkflow] = {}

    def create_workflow(self, title_cn: str) -> MultiAgentWorkflow:
        wf_id = f"wf-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        wf = MultiAgentWorkflow(
            workflow_id=wf_id, title_cn=title_cn, state=WorkflowState.PLANNING,
            state_history=[{"from_state": None, "to_state": WorkflowState.PLANNING.value, "at": now, "note": "工作流创建"}],
            created_at=now, updated_at=now,
        )
        self._workflows[wf_id] = wf
        return wf

    def list_workflows(self) -> list[MultiAgentWorkflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> Optional[MultiAgentWorkflow]:
        return self._workflows.get(workflow_id)

    def status_summary_cn(self, workflow_id: str) -> dict:
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return {"error": f"未找到工作流：{workflow_id}"}
        summary = _STATE_SUMMARIES_CN.get(wf.state, "未知状态。")
        valid_transitions = _VALID_TRANSITIONS.get(wf.state, [])
        next_map = {
            WorkflowState.PLANNING: ["规划者完成计划后进入待构建状态"],
            WorkflowState.READY_FOR_BUILD: ["构建者开始实现代码"],
            WorkflowState.BUILDING: ["构建者完成后进入待审查状态"],
            WorkflowState.READY_FOR_REVIEW: ["审查者开始独立审查（不能与构建者同一上下文）"],
            WorkflowState.REVIEWING: ["审查通过→已批准", "发现问题→需修改", "严重问题→已阻塞"],
            WorkflowState.CHANGES_REQUESTED: ["构建者根据审查意见修复后重新提交"],
            WorkflowState.BLOCKED: ["需人工介入解决阻塞原因", "或重新规划"],
        }
        next_steps = next_map.get(wf.state, ["工作流已结束"])
        return {
            "workflow_id": wf.workflow_id, "title_cn": wf.title_cn,
            "state": wf.state.value, "state_label_cn": wf.state.label_cn,
            "summary_cn": summary, "next_steps_cn": next_steps,
            "valid_transitions": [t.value for t in valid_transitions],
            "blocked_reason_cn": wf.blocked_reason_cn or None,
            "has_planner_output": wf.planner_output is not None,
            "has_builder_output": wf.builder_output is not None,
            "has_reviewer_output": wf.reviewer_output is not None,
        }

    def assign_planner_output(self, workflow_id: str, task_breakdown: list[dict],
                              risk_assessment: str, assignment: dict,
                              source_refs: list[str], context: str = "") -> TransitionResult:
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)
        if wf.state != WorkflowState.PLANNING:
            return TransitionResult(False, f"当前状态 {wf.state.label_cn} 不允许提交规划输出。", blocked=True)
        if not source_refs:
            return TransitionResult(False, "规划输出必须包含 source_refs。", blocked=True)
        wf.planner_output = PlannerOutput(task_breakdown=task_breakdown, risk_assessment=risk_assessment,
                                          assignment=assignment, source_refs=source_refs,
                                          submitted_at=datetime.now(timezone.utc).isoformat(), submitted_by_context=context)
        return self._transition(wf, WorkflowState.READY_FOR_BUILD, "规划者提交计划")

    def assign_builder_output(self, workflow_id: str, code_changes: str, tests: str,
                              evidence_refs: list[str], source_refs: list[str],
                              context: str = "") -> TransitionResult:
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)
        if wf.state not in (WorkflowState.BUILDING, WorkflowState.CHANGES_REQUESTED):
            return TransitionResult(False, f"当前状态 {wf.state.label_cn} 不允许提交构建输出。", blocked=True)
        if not evidence_refs:
            return TransitionResult(False, "构建输出必须包含 evidence_refs。", blocked=True)
        if wf.reviewer_output and wf.reviewer_output.submitted_by_context == context:
            return TransitionResult(False, "构建者不能与审查者使用同一上下文（自我批准）。", blocked=True)
        wf.builder_output = BuilderOutput(code_changes=code_changes, tests=tests, evidence_refs=evidence_refs,
                                          source_refs=source_refs, submitted_at=datetime.now(timezone.utc).isoformat(),
                                          submitted_by_context=context)
        if wf.state == WorkflowState.CHANGES_REQUESTED:
            r = self._transition(wf, WorkflowState.BUILDING, "构建者开始修复")
            if not r.valid:
                return r
        return self._transition(wf, WorkflowState.READY_FOR_REVIEW, "构建者提交实现")

    def assign_reviewer_output(self, workflow_id: str, findings: list[dict], evidence: list[str],
                               tests_status: str, residual_risks: list[str], verdict: str,
                               source_refs: list[str], context: str = "") -> TransitionResult:
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)
        if wf.state != WorkflowState.READY_FOR_REVIEW:
            return TransitionResult(False, f"当前状态 {wf.state.label_cn} 不允许提交审查输出。", blocked=True)
        if wf.builder_output and wf.builder_output.submitted_by_context == context:
            return TransitionResult(False, "审查者不能与构建者使用同一上下文（自我批准）。", blocked=True)
        if not evidence and not source_refs:
            return TransitionResult(False, "审查输出必须包含 evidence 或 source_refs。", blocked=True)
        if verdict not in ("approved", "changes_requested", "blocked"):
            return TransitionResult(False, f"无效审查结论：{verdict}。", blocked=True)
        if verdict == "approved":
            p1_p2 = [f for f in findings if f.get("severity", "").upper() in ("P1", "P2")]
            if p1_p2:
                return TransitionResult(False, f"存在 {len(p1_p2)} 个未修复 P1/P2，不能批准。", blocked=True)
            if not tests_status:
                return TransitionResult(False, "审查通过需要 tests_status。", blocked=True)
        wf.reviewer_output = ReviewerOutput(findings=findings, evidence=evidence, tests_status=tests_status,
                                            residual_risks=residual_risks, verdict=verdict, source_refs=source_refs,
                                            submitted_at=datetime.now(timezone.utc).isoformat(), submitted_by_context=context)
        r = self._transition(wf, WorkflowState.REVIEWING, "审查者开始审查")
        if not r.valid:
            return r
        target = {"approved": WorkflowState.APPROVED, "changes_requested": WorkflowState.CHANGES_REQUESTED,
                  "blocked": WorkflowState.BLOCKED}[verdict]
        if verdict == "blocked":
            wf.blocked_reason_cn = "审查者标记为阻塞。" + (f" 发现 {len(findings)} 个问题。" if findings else "")
        return self._transition(wf, target, f"审查者结论：{verdict}")

    def validate_transition(self, workflow_id: str, target_state: str) -> TransitionResult:
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)
        try:
            target = WorkflowState(target_state)
        except ValueError:
            return TransitionResult(False, f"无效状态：{target_state}。", blocked=True)
        valid = _VALID_TRANSITIONS.get(wf.state, [])
        if target not in valid:
            return TransitionResult(False, f"不允许 {wf.state.label_cn}→{target.label_cn}。", blocked=True)
        return TransitionResult(True, f"转移 {wf.state.label_cn}→{target.label_cn} 有效。")

    def _transition(self, wf: MultiAgentWorkflow, to_state: WorkflowState, note: str = "") -> TransitionResult:
        valid = _VALID_TRANSITIONS.get(wf.state, [])
        if to_state not in valid:
            return TransitionResult(False, f"不允许 {wf.state.label_cn}→{to_state.label_cn}。", blocked=True)
        from_state = wf.state
        wf.state = to_state
        wf.updated_at = datetime.now(timezone.utc).isoformat()
        wf.state_history.append({"from_state": from_state.value, "to_state": to_state.value,
                                 "at": wf.updated_at, "note": note})
        return TransitionResult(True, f"转移完成：{from_state.label_cn}→{to_state.label_cn}。{note}", to_state)
