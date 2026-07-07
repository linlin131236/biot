"""Multi-Agent Workflow data models: states, transitions, output types.

Extracted from multi_agent_workflow.py to respect the 300-line size gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
        _labels = {
            "planning": "规划中", "ready_for_build": "待构建",
            "building": "构建中", "ready_for_review": "待审查",
            "reviewing": "审查中", "changes_requested": "需修改",
            "approved": "已批准", "blocked": "已阻塞", "failed": "已失败",
        }
        return _labels.get(self.value, self.value)


_VALID_TRANSITIONS: dict[WorkflowState, list[WorkflowState]] = {
    WorkflowState.PLANNING: [WorkflowState.READY_FOR_BUILD, WorkflowState.FAILED, WorkflowState.BLOCKED],
    WorkflowState.READY_FOR_BUILD: [WorkflowState.BUILDING, WorkflowState.FAILED],
    WorkflowState.BUILDING: [WorkflowState.READY_FOR_REVIEW, WorkflowState.FAILED, WorkflowState.BLOCKED],
    WorkflowState.READY_FOR_REVIEW: [WorkflowState.REVIEWING, WorkflowState.FAILED],
    WorkflowState.REVIEWING: [WorkflowState.APPROVED, WorkflowState.CHANGES_REQUESTED,
                               WorkflowState.BLOCKED, WorkflowState.FAILED],
    WorkflowState.CHANGES_REQUESTED: [WorkflowState.BUILDING, WorkflowState.FAILED],
    WorkflowState.APPROVED: [],
    WorkflowState.BLOCKED: [WorkflowState.PLANNING, WorkflowState.FAILED],
    WorkflowState.FAILED: [],
}

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


@dataclass
class PlannerOutput:
    task_breakdown: list[dict]
    risk_assessment: str
    assignment: dict
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "task_breakdown": self.task_breakdown, "risk_assessment": self.risk_assessment,
            "assignment": self.assignment, "source_refs": self.source_refs,
            "submitted_at": self.submitted_at, "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class BuilderOutput:
    code_changes: str
    tests: str
    evidence_refs: list[str]
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "code_changes": self.code_changes, "tests": self.tests,
            "evidence_refs": self.evidence_refs, "source_refs": self.source_refs,
            "submitted_at": self.submitted_at, "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class ReviewerOutput:
    findings: list[dict]
    evidence: list[str]
    tests_status: str
    residual_risks: list[str]
    verdict: str
    source_refs: list[str]
    submitted_at: str = ""
    submitted_by_context: str = ""

    def to_dict(self) -> dict:
        return {
            "findings": self.findings, "evidence": self.evidence,
            "tests_status": self.tests_status, "residual_risks": self.residual_risks,
            "verdict": self.verdict, "source_refs": self.source_refs,
            "submitted_at": self.submitted_at, "submitted_by_context": self.submitted_by_context,
        }


@dataclass
class MultiAgentWorkflow:
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
            "workflow_id": self.workflow_id, "title_cn": self.title_cn,
            "state": self.state.value, "state_label_cn": self.state.label_cn,
            "planner_output": self.planner_output.to_dict() if self.planner_output else None,
            "builder_output": self.builder_output.to_dict() if self.builder_output else None,
            "reviewer_output": self.reviewer_output.to_dict() if self.reviewer_output else None,
            "state_history": self.state_history, "created_at": self.created_at,
            "updated_at": self.updated_at, "blocked_reason_cn": self.blocked_reason_cn,
        }


@dataclass
class TransitionResult:
    valid: bool
    message_cn: str
    new_state: Optional[WorkflowState] = None
    details: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid, "message_cn": self.message_cn,
            "new_state": self.new_state.value if self.new_state else None,
            "details": self.details, "blocked": self.blocked,
        }
