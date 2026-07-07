"""SkillLearner Review Loop. Analyzes repeated failures to propose
workflow/skill/doc improvements. Proposes A/B/C options, never modifies
business code or skill files directly. Requires father approval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


# Minimum same-class failures to trigger analysis
_MIN_FAILURES_FOR_PATTERN = 2


class ProposalTarget(str):
    WORKFLOW_DOC = "workflow_doc"
    SKILL_DOC = "skill_doc"
    REVIEW_POLICY = "review_policy"
    UNKNOWN = "unknown"

    @property
    def label_cn(self) -> str:
        return {
            "workflow_doc": "工作流文档",
            "skill_doc": "技能文档",
            "review_policy": "审查策略",
            "unknown": "未知",
        }.get(self, self)


@dataclass
class FailurePattern:
    """A detected pattern of repeated failures."""
    failure_class: str  # from M64 FailureClassifier
    count: int
    examples: list[str]  # failure IDs or descriptions
    last_occurred_at: str

    def to_dict(self) -> dict:
        return {
            "failure_class": self.failure_class,
            "count": self.count,
            "examples": self.examples,
            "last_occurred_at": self.last_occurred_at,
        }


@dataclass
class ImprovementProposal:
    """A/B/C improvement proposal from SkillLearner."""
    proposal_id: str
    title_cn: str
    triggered_by: FailurePattern
    target_type: str  # workflow_doc / skill_doc / review_policy / unknown
    target_label_cn: str
    options: list[dict]  # [{option: "A"/"B"/"C", label, impact_cn}]
    evidence_refs: list[str]
    source_refs: list[str]
    requires_father_approval: bool  # always True
    created_at: str

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "title_cn": self.title_cn,
            "triggered_by": self.triggered_by.to_dict(),
            "target_type": self.target_type,
            "target_label_cn": self.target_label_cn,
            "options": self.options,
            "evidence_refs": self.evidence_refs,
            "source_refs": self.source_refs,
            "requires_father_approval": self.requires_father_approval,
            "created_at": self.created_at,
            "note": "此提案为只读建议，不直接修改任何文件。必须等待爸爸审批后才能应用。",
        }


class SkillLearnerReviewLoopService:
    """Collects failures, detects patterns, generates improvement proposals.
    NEVER modifies business code or skill files."""

    def __init__(self) -> None:
        self._failures: list[dict] = []  # [{failure_class, failure_id, desc, at}]
        self._proposals: dict[str, ImprovementProposal] = {}

    def record_failure(
        self,
        failure_class: str,
        failure_id: str,
        description_cn: str,
    ) -> dict:
        """Record a failure for pattern analysis."""
        entry = {
            "failure_class": failure_class,
            "failure_id": failure_id,
            "description_cn": description_cn,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        self._failures.append(entry)
        return {"recorded": True, "total_failures": len(self._failures)}

    def analyze(self) -> dict:
        """Analyze recorded failures for patterns. Only triggers when
        same-class failures >= 2.

        Returns: { patterns_found: bool, patterns: [...], proposal_count: int }
        """
        # Group by failure_class
        groups: dict[str, list[dict]] = {}
        for f in self._failures:
            cls = f["failure_class"]
            groups.setdefault(cls, []).append(f)

        patterns: list[FailurePattern] = []
        for cls, entries in groups.items():
            if len(entries) >= _MIN_FAILURES_FOR_PATTERN:
                patterns.append(FailurePattern(
                    failure_class=cls,
                    count=len(entries),
                    examples=[e["failure_id"] for e in entries[-3:]],
                    last_occurred_at=entries[-1]["occurred_at"],
                ))

        return {
            "patterns_found": len(patterns) > 0,
            "patterns": [p.to_dict() for p in patterns],
            "total_failures_recorded": len(self._failures),
            "note": f"同类失败 >= {_MIN_FAILURES_FOR_PATTERN} 次触发技能缺陷分析。当前 {len(patterns)} 个模式。",
        }

    def propose_improvement(
        self,
        title_cn: str,
        failure_class: str,
        options: list[dict] | None = None,
        target_type: str = "unknown",
        evidence_refs: list[str] | None = None,
        source_refs: list[str] | None = None,
    ) -> ImprovementProposal:
        """Generate an improvement proposal with A/B/C options.

        NEVER modifies files. Requires father approval to apply.
        """
        # Find the pattern
        entries = [f for f in self._failures if f["failure_class"] == failure_class]
        pattern = FailurePattern(
            failure_class=failure_class,
            count=len(entries),
            examples=[e["failure_id"] for e in entries[-3:]],
            last_occurred_at=entries[-1]["occurred_at"] if entries else "",
        )

        default_options = options or [
            {"option": "A", "label": "更新流程文档，增加检查步骤", "impact_cn": "文档变更，无代码影响"},
            {"option": "B", "label": "创建自动化检查脚本", "impact_cn": "需要开发和测试"},
            {"option": "C", "label": "调整审查策略，增加针对性检查", "impact_cn": "审查流程变更"},
        ]

        proposal = ImprovementProposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
            title_cn=title_cn,
            triggered_by=pattern,
            target_type=target_type,
            target_label_cn=ProposalTarget(target_type).label_cn if target_type in ("workflow_doc", "skill_doc", "review_policy") else "未知",
            options=default_options,
            evidence_refs=evidence_refs or [],
            source_refs=source_refs or [],
            requires_father_approval=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def list_proposals(self) -> list[ImprovementProposal]:
        return list(self._proposals.values())

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        return self._proposals.get(proposal_id)

    def total_failures(self) -> int:
        return len(self._failures)
