"""Multi-Agent Workflow state machine. Orchestrates Planner → Builder →
Reviewer pipeline with strict transition validation.

Principles from Flock (role-based pipeline, Arbiter loop breaker) and
Phase16 (Supervisor orchestration, role specialization):
- Builder cannot self-approve.
- Reviewer cannot modify builder output.
- Every transition validates evidence/source_refs.
- No code execution or file modification — pure state management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


# ── Workflow states ────────────────────────────────────────────────────

class WorkflowState(str, Enum):
    PLANNING = "planning"
    READY_FOR_BUILD = "ready_for_build"
    BUILDING = "building"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWING = "reviewing"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    BLOCKED = "blocked"
    FAILED = "failed"

    @property
    def label_cn(self) -> str:
        _labels: dict[str, str] = {
            "planning": "规划中",
            "ready_for_build": "待构建",
            "building": "构建中",
            "ready_for_review": "待审查",
            "reviewing": "审查中",
            "changes_requested": "需修改",
            "approved": "已批准",
            "blocked": "已阻塞",
            "failed": "已失败",
        }
        return _labels.get(self.value, self.value)


# ── Allowed transitions (from → list of valid to states) ──────────────

_VALID_TRANSITIONS: dict[WorkflowState, list[WorkflowState]] = {
    WorkflowState.PLANNING: [
        WorkflowState.READY_FOR_BUILD,
        WorkflowState.FAILED,
        WorkflowState.BLOCKED,
    ],
    WorkflowState.READY_FOR_BUILD: [
        WorkflowState.BUILDING,
        WorkflowState.FAILED,
    ],
    WorkflowState.BUILDING: [
        WorkflowState.READY_FOR_REVIEW,
        WorkflowState.FAILED,
        WorkflowState.BLOCKED,
    ],
    WorkflowState.READY_FOR_REVIEW: [
        WorkflowState.REVIEWING,
        WorkflowState.FAILED,
    ],
    WorkflowState.REVIEWING: [
        WorkflowState.APPROVED,
        WorkflowState.CHANGES_REQUESTED,
        WorkflowState.BLOCKED,
        WorkflowState.FAILED,
    ],
    WorkflowState.CHANGES_REQUESTED: [
        WorkflowState.BUILDING,
        WorkflowState.FAILED,
    ],
    WorkflowState.APPROVED: [],  # terminal
    WorkflowState.BLOCKED: [
        WorkflowState.PLANNING,  # re-plan
        WorkflowState.FAILED,
    ],
    WorkflowState.FAILED: [],  # terminal
}

# ── State summary templates in Chinese ─────────────────────────────────

_STATE_SUMMARIES_CN: dict[WorkflowState, str] = {
    WorkflowState.PLANNING: "规划者正在分解任务和定义验收标准。此阶段不执行代码。",
    WorkflowState.READY_FOR_BUILD: "规划已完成，等待构建者开始实现。",
    WorkflowState.BUILDING: "构建者正在实现代码和编写测试。构建者不能自我批准。",
    WorkflowState.READY_FOR_REVIEW: "构建完成，等待独立审查者进行评估。",
    WorkflowState.REVIEWING: "审查者正在独立评估代码质量。审查者只审不改。",
    WorkflowState.CHANGES_REQUESTED: "审查发现需要修改，构建者需根据审查意见修复。",
    WorkflowState.APPROVED: "审查通过，工作流已完成。",
    WorkflowState.BLOCKED: "工作流被阻塞，需人工介入解决阻塞原因。",
    WorkflowState.FAILED: "工作流失败，需检查失败原因后重新规划或人工处理。",
}

# ── Data models ────────────────────────────────────────────────────────

@dataclass
class PlannerOutput:
    """Output from Planner role. Attached to workflow."""
    task_breakdown: list[dict]
    risk_assessment: str  # low/medium/high/critical
    assignment: dict  # {task_id: role_id}
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "task_breakdown": self.task_breakdown,
            "risk_assessment": self.risk_assessment,
            "assignment": self.assignment,
            "source_refs": self.source_refs,
            "submitted_at": self.submitted_at,
            "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class BuilderOutput:
    """Output from Builder role. Attached to workflow."""
    code_changes: str  # summary of changes
    tests: str  # test results summary
    evidence_refs: list[str]
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "code_changes": self.code_changes,
            "tests": self.tests,
            "evidence_refs": self.evidence_refs,
            "source_refs": self.source_refs,
            "submitted_at": self.submitted_at,
            "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class ReviewerOutput:
    """Output from Reviewer role. Attached to workflow."""
    findings: list[dict]  # [{severity, desc, location}]
    evidence: list[str]
    tests_status: str
    residual_risks: list[str]
    verdict: str  # approved / changes_requested / blocked
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "findings": self.findings,
            "evidence": self.evidence,
            "tests_status": self.tests_status,
            "residual_risks": self.residual_risks,
            "verdict": self.verdict,
            "source_refs": self.source_refs,
            "submitted_at": self.submitted_at,
            "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class MultiAgentWorkflow:
    """A single Planner → Builder → Reviewer workflow instance.

    Read-only state management. Never auto-executes code or modifies files."""
    workflow_id: str
    title_cn: str
    state: WorkflowState
    planner_output: Optional[PlannerOutput] = None
    builder_output: Optional[BuilderOutput] = None
    reviewer_output: Optional[ReviewerOutput] = None
    state_history: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    blocked_reason_cn: str = ""

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "title_cn": self.title_cn,
            "state": self.state.value,
            "state_label_cn": self.state.label_cn,
            "planner_output": self.planner_output.to_dict() if self.planner_output else None,
            "builder_output": self.builder_output.to_dict() if self.builder_output else None,
            "reviewer_output": self.reviewer_output.to_dict() if self.reviewer_output else None,
            "state_history": self.state_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "blocked_reason_cn": self.blocked_reason_cn,
        }


@dataclass
class TransitionResult:
    """Result of a state transition validation or execution."""
    valid: bool
    message_cn: str
    new_state: Optional[WorkflowState] = None
    details: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "message_cn": self.message_cn,
            "new_state": self.new_state.value if self.new_state else None,
            "details": self.details,
            "blocked": self.blocked,
        }


# ── Service ─────────────────────────────────────────────────────────────

class MultiAgentWorkflowService:
    """Manages multi-agent workflows. Pure state machine; no execution."""

    def __init__(self) -> None:
        self._workflows: dict[str, MultiAgentWorkflow] = {}

    # ── Create ──────────────────────────────────────────────────────

    def create_workflow(self, title_cn: str) -> MultiAgentWorkflow:
        """Create a new workflow in planning state."""
        wf_id = f"wf-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        wf = MultiAgentWorkflow(
            workflow_id=wf_id,
            title_cn=title_cn,
            state=WorkflowState.PLANNING,
            state_history=[{
                "from_state": None,
                "to_state": WorkflowState.PLANNING.value,
                "at": now,
                "note": "工作流创建",
            }],
            created_at=now,
            updated_at=now,
        )
        self._workflows[wf_id] = wf
        return wf

    # ── Read ────────────────────────────────────────────────────────

    def list_workflows(self) -> list[MultiAgentWorkflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> Optional[MultiAgentWorkflow]:
        return self._workflows.get(workflow_id)

    def status_summary_cn(self, workflow_id: str) -> dict:
        """Chinese status summary for a workflow."""
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return {"error": f"未找到工作流：{workflow_id}"}

        summary = _STATE_SUMMARIES_CN.get(wf.state, "未知状态。")
        next_steps: list[str] = []
        valid_transitions = _VALID_TRANSITIONS.get(wf.state, [])

        if wf.state == WorkflowState.PLANNING:
            next_steps = ["规划者完成计划后进入待构建状态"]
        elif wf.state == WorkflowState.READY_FOR_BUILD:
            next_steps = ["构建者开始实现代码"]
        elif wf.state == WorkflowState.BUILDING:
            next_steps = ["构建者完成后进入待审查状态"]
        elif wf.state == WorkflowState.READY_FOR_REVIEW:
            next_steps = ["审查者开始独立审查（不能与构建者同一上下文）"]
        elif wf.state == WorkflowState.REVIEWING:
            next_steps = [
                "审查通过 → 已批准",
                "发现问题 → 需修改（返回构建者）",
                "严重问题 → 已阻塞",
            ]
        elif wf.state == WorkflowState.CHANGES_REQUESTED:
            next_steps = ["构建者根据审查意见修复后重新提交"]
        elif wf.state == WorkflowState.BLOCKED:
            next_steps = ["需人工介入解决阻塞原因", "或重新规划"]
        elif wf.state in (WorkflowState.APPROVED, WorkflowState.FAILED):
            next_steps = ["工作流已结束"]

        return {
            "workflow_id": wf.workflow_id,
            "title_cn": wf.title_cn,
            "state": wf.state.value,
            "state_label_cn": wf.state.label_cn,
            "summary_cn": summary,
            "next_steps_cn": next_steps,
            "valid_transitions": [t.value for t in valid_transitions],
            "blocked_reason_cn": wf.blocked_reason_cn or None,
            "has_planner_output": wf.planner_output is not None,
            "has_builder_output": wf.builder_output is not None,
            "has_reviewer_output": wf.reviewer_output is not None,
        }

    # ── Assign outputs (with transition) ────────────────────────────

    def assign_planner_output(
        self,
        workflow_id: str,
        task_breakdown: list[dict],
        risk_assessment: str,
        assignment: dict,
        source_refs: list[str],
        context: str = "",
    ) -> TransitionResult:
        """Assign planner output. Transitions: planning → ready_for_build."""
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)

        if wf.state != WorkflowState.PLANNING:
            return TransitionResult(
                False,
                f"当前状态 {wf.state.label_cn} 不允许提交规划输出。需要状态为规划中。",
                details=[f"当前状态：{wf.state.value}"],
                blocked=True,
            )

        if not source_refs:
            return TransitionResult(
                False,
                "规划输出必须包含 source_refs（参考资料引用）。",
                blocked=True,
            )

        wf.planner_output = PlannerOutput(
            task_breakdown=task_breakdown,
            risk_assessment=risk_assessment,
            assignment=assignment,
            source_refs=source_refs,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            submitted_by_context=context,
        )
        result = self._transition(wf, WorkflowState.READY_FOR_BUILD, "规划者提交计划")
        return result

    def assign_builder_output(
        self,
        workflow_id: str,
        code_changes: str,
        tests: str,
        evidence_refs: list[str],
        source_refs: list[str],
        context: str = "",
    ) -> TransitionResult:
        """Assign builder output. Transitions: building → ready_for_review."""
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)

        if wf.state not in (WorkflowState.BUILDING, WorkflowState.CHANGES_REQUESTED):
            return TransitionResult(
                False,
                f"当前状态 {wf.state.label_cn} 不允许提交构建输出。"
                f"需要状态为构建中或需修改。",
                details=[f"当前状态：{wf.state.value}"],
                blocked=True,
            )

        if not evidence_refs:
            return TransitionResult(
                False,
                "构建输出必须包含 evidence_refs（测试结果等证据）。",
                blocked=True,
            )

        # Self-approval check: builder context must not match reviewer context
        if wf.reviewer_output and wf.reviewer_output.submitted_by_context == context:
            return TransitionResult(
                False,
                "构建者不能与审查者使用同一上下文。这是自我批准，不允许。",
                details=[
                    "构建者上下文与审查者上下文相同。",
                    "请使用独立的审查者上下文进行评估。",
                ],
                blocked=True,
            )

        wf.builder_output = BuilderOutput(
            code_changes=code_changes,
            tests=tests,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            submitted_by_context=context,
        )
        # If coming from changes_requested, first transition to building
        if wf.state == WorkflowState.CHANGES_REQUESTED:
            result = self._transition(wf, WorkflowState.BUILDING, "构建者开始修复")
            if not result.valid:
                return result
        result = self._transition(wf, WorkflowState.READY_FOR_REVIEW, "构建者提交实现")
        return result

    def assign_reviewer_output(
        self,
        workflow_id: str,
        findings: list[dict],
        evidence: list[str],
        tests_status: str,
        residual_risks: list[str],
        verdict: str,
        source_refs: list[str],
        context: str = "",
    ) -> TransitionResult:
        """Assign reviewer output and transition based on verdict.

        Verdict → target state:
        - approved → approved
        - changes_requested → changes_requested
        - blocked → blocked

        Hard rules:
        - Reviewer context must differ from builder context (no self-approval)
        - Must have evidence and source_refs
        - Reviewer cannot modify builder output (read-only)
        """
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)

        if wf.state != WorkflowState.READY_FOR_REVIEW:
            return TransitionResult(
                False,
                f"当前状态 {wf.state.label_cn} 不允许提交审查输出。"
                f"需要状态为待审查。",
                details=[f"当前状态：{wf.state.value}"],
                blocked=True,
            )

        # Self-approval prevention
        if wf.builder_output and wf.builder_output.submitted_by_context == context:
            return TransitionResult(
                False,
                "审查者不能与构建者使用同一上下文。构建者不能审查自己的工作。",
                details=[
                    f"构建者上下文：{wf.builder_output.submitted_by_context}",
                    f"审查者上下文：{context}",
                    "两者相同，构成自我批准，不允许。",
                ],
                blocked=True,
            )

        # Evidence check
        if not evidence and not source_refs:
            return TransitionResult(
                False,
                "审查输出必须包含 evidence（发现证据）或 source_refs。",
                blocked=True,
            )

        # Verdict validation
        valid_verdicts = {"approved", "changes_requested", "blocked"}
        if verdict not in valid_verdicts:
            return TransitionResult(
                False,
                f"审查结论无效：{verdict}。有效值：approved / changes_requested / blocked。",
                blocked=True,
            )

        # P1/P2 findings without fix → cannot approve
        if verdict == "approved":
            p1_p2 = [f for f in findings if f.get("severity", "").upper() in ("P1", "P2")]
            if p1_p2:
                return TransitionResult(
                    False,
                    "存在未修复的 P1/P2 问题，不能批准。请先修复后再审查。",
                    details=[f"P1/P2 问题数：{len(p1_p2)}"],
                    blocked=True,
                )
            if not tests_status:
                return TransitionResult(
                    False,
                    "审查通过需要测试状态评估（tests_status）。",
                    blocked=True,
                )

        wf.reviewer_output = ReviewerOutput(
            findings=findings,
            evidence=evidence,
            tests_status=tests_status,
            residual_risks=residual_risks,
            verdict=verdict,
            source_refs=source_refs,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            submitted_by_context=context,
        )

        # First transition: ready_for_review → reviewing (reviewer starts work)
        result = self._transition(wf, WorkflowState.REVIEWING, "审查者开始审查")
        if not result.valid:
            return result

        # Second transition: reviewing → verdict state (reviewer submits conclusion)
        verdict_state_map = {
            "approved": WorkflowState.APPROVED,
            "changes_requested": WorkflowState.CHANGES_REQUESTED,
            "blocked": WorkflowState.BLOCKED,
        }
        target_state = verdict_state_map[verdict]

        note = f"审查者结论：{verdict}"
        if verdict == "blocked":
            wf.blocked_reason_cn = "审查者标记为阻塞。" + (
                f" 发现 {len(findings)} 个问题。" if findings else ""
            )

        return self._transition(wf, target_state, note)

    # ── Transition validation (diagnostic, no state change) ──────────

    def validate_transition(
        self,
        workflow_id: str,
        target_state: str,
    ) -> TransitionResult:
        """Diagnostic check: is this transition valid? Does not change state."""
        wf = self.get_workflow(workflow_id)
        if wf is None:
            return TransitionResult(False, f"未找到工作流：{workflow_id}", blocked=True)

        try:
            target = WorkflowState(target_state)
        except ValueError:
            return TransitionResult(
                False,
                f"无效的目标状态：{target_state}。有效状态："
                f"{', '.join(s.value for s in WorkflowState)}。",
                blocked=True,
            )

        valid_targets = _VALID_TRANSITIONS.get(wf.state, [])
        if target not in valid_targets:
            return TransitionResult(
                False,
                f"不允许从 {wf.state.label_cn} 转移到 {target.label_cn}。",
                details=[
                    f"当前状态 {wf.state.value} 允许的转移："
                    f"{', '.join(t.value for t in valid_targets)}。"
                ],
                blocked=True,
            )

        return TransitionResult(
            True,
            f"转移 {wf.state.label_cn} → {target.label_cn} 有效。",
        )

    # ── Internal ─────────────────────────────────────────────────────

    def _transition(
        self,
        wf: MultiAgentWorkflow,
        to_state: WorkflowState,
        note: str = "",
    ) -> TransitionResult:
        """Execute a state transition. Validates first, then changes state."""
        valid_targets = _VALID_TRANSITIONS.get(wf.state, [])
        if to_state not in valid_targets:
            return TransitionResult(
                False,
                f"不允许从 {wf.state.label_cn} 转移到 {to_state.label_cn}。",
                details=[
                    f"允许的转移：{', '.join(t.value for t in valid_targets)}。"
                ],
                blocked=True,
            )

        from_state = wf.state
        wf.state = to_state
        wf.updated_at = datetime.now(timezone.utc).isoformat()
        wf.state_history.append({
            "from_state": from_state.value,
            "to_state": to_state.value,
            "at": wf.updated_at,
            "note": note,
        })

        return TransitionResult(
            valid=True,
            message_cn=f"状态转移完成：{from_state.label_cn} → {to_state.label_cn}。{note}",
            new_state=to_state,
        )
