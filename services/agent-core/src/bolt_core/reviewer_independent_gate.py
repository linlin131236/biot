"""Reviewer Independent Gate. Ensures reviewer judgments are independent
from builder context. Prevents self-approval, enforces evidence, and
classifies results as approved / changes_requested / blocked.

M85 is a milestone judgment point for father's long-term use — must be strict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


# ── Data ────────────────────────────────────────────────────────────────

@dataclass
class ReviewPackage:
    """What gets submitted for review."""
    review_id: str
    workflow_id: str
    builder_context: str
    reviewer_context: str
    builder_output_summary: str
    code_changes: str
    tests_status: str
    evidence_refs: list[str]
    source_refs: list[str]
    submitted_at: str = ""

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "workflow_id": self.workflow_id,
            "builder_context": self.builder_context,
            "reviewer_context": self.reviewer_context,
            "builder_output_summary": self.builder_output_summary,
            "code_changes": self.code_changes,
            "tests_status": self.tests_status,
            "evidence_refs": self.evidence_refs,
            "source_refs": self.source_refs,
            "submitted_at": self.submitted_at,
        }


class ReviewVerdict(str):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"

    @property
    def label_cn(self) -> str:
        return {"approved": "已批准", "changes_requested": "需修改", "blocked": "已阻塞"}.get(self, self)


@dataclass
class ReviewGateResult:
    review_id: str
    verdict: str
    verdict_label_cn: str
    findings: list[dict]
    evidence: list[str]
    tests_status: str
    residual_risks: list[str]
    source_refs: list[str]
    is_self_approval: bool
    summary_cn: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "verdict": self.verdict,
            "verdict_label_cn": self.verdict_label_cn,
            "findings": self.findings,
            "evidence": self.evidence,
            "tests_status": self.tests_status,
            "residual_risks": self.residual_risks,
            "source_refs": self.source_refs,
            "is_self_approval": self.is_self_approval,
            "summary_cn": self.summary_cn,
            "created_at": self.created_at,
        }


# ── Service ─────────────────────────────────────────────────────────────

class ReviewerIndependentGateService:
    """Evaluates review packages with strict independence rules."""

    def __init__(self) -> None:
        self._results: dict[str, ReviewGateResult] = {}

    def evaluate(
        self,
        workflow_id: str,
        builder_context: str,
        reviewer_context: str,
        builder_output_summary: str,
        code_changes: str,
        tests_status: str,
        evidence_refs: list[str],
        source_refs: list[str],
        findings: list[dict] | None = None,
        residual_risks: list[str] | None = None,
    ) -> ReviewGateResult:
        """Evaluate a review package.

        Hard blocks:
        - Self-approval (builder_context == reviewer_context)
        - No evidence + no source_refs
        - Tests missing with no explanation

        Verdict rules:
        - Self-approval → BLOCKED
        - P1 findings → BLOCKED
        - P2 findings → CHANGES_REQUESTED
        - No issues → APPROVED
        """
        findings_list = findings or []
        risks = residual_risks or []
        review_id = f"rev-{uuid.uuid4().hex[:8]}"
        is_self = builder_context == reviewer_context

        # Self-approval = immediate BLOCKED
        if is_self:
            result = ReviewGateResult(
                review_id=review_id,
                verdict="blocked",
                verdict_label_cn="已阻塞",
                findings=[{"severity": "P1", "desc": "自我批准：构建者与审查者上下文相同", "location": "reviewer_context"}],
                evidence=evidence_refs,
                tests_status=tests_status,
                residual_risks=risks + ["审查者与构建者同上下文，审查无效"],
                source_refs=source_refs,
                is_self_approval=True,
                summary_cn="审查被阻塞：构建者不能审查自己的工作。请使用独立的审查者上下文重新提交。",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._results[review_id] = result
            return result

        # No evidence check
        if not evidence_refs and not source_refs:
            result = ReviewGateResult(
                review_id=review_id,
                verdict="blocked",
                verdict_label_cn="已阻塞",
                findings=[{"severity": "P1", "desc": "审查缺少证据：evidence_refs 和 source_refs 均为空", "location": "review_package"}],
                evidence=[],
                tests_status=tests_status,
                residual_risks=risks,
                source_refs=source_refs,
                is_self_approval=False,
                summary_cn="审查被阻塞：审查必须提供 evidence_refs 或 source_refs。",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._results[review_id] = result
            return result

        # Classify by findings
        has_p1 = any(f.get("severity", "").upper() == "P1" for f in findings_list)
        has_p2 = any(f.get("severity", "").upper() == "P2" for f in findings_list)

        if has_p1:
            verdict = "blocked"
            verdict_label = "已阻塞"
            summary = "审查被阻塞：存在 P1 问题，必须先修复后再审查。"
        elif has_p2:
            verdict = "changes_requested"
            verdict_label = "需修改"
            summary = "审查发现 P2 问题，需构建者修改后重新提交审查。"
        elif not tests_status:
            verdict = "changes_requested"
            verdict_label = "需修改"
            summary = "审查需要测试状态评估。请补充 tests_status 后重新提交。"
        else:
            verdict = "approved"
            verdict_label = "已批准"
            summary = "审查通过。所有检查项达标。"

        result = ReviewGateResult(
            review_id=review_id,
            verdict=verdict,
            verdict_label_cn=verdict_label,
            findings=findings_list,
            evidence=evidence_refs,
            tests_status=tests_status,
            residual_risks=risks,
            source_refs=source_refs,
            is_self_approval=False,
            summary_cn=summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._results[review_id] = result
        return result

    def get_result(self, review_id: str) -> Optional[ReviewGateResult]:
        return self._results.get(review_id)

    def list_results(self) -> list[ReviewGateResult]:
        return list(self._results.values())
