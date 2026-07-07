"""Conflict Resolution. Detects and classifies conflicts between
Planner/Builder/Reviewer/Researcher roles. Proposes resolution options
but never auto-resolves high-risk conflicts.

Conflict types: scope, evidence, implementation, review, safety, preference, unknown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class ConflictType(str, Enum):
    SCOPE = "scope_conflict"
    EVIDENCE = "evidence_conflict"
    IMPLEMENTATION = "implementation_conflict"
    REVIEW = "review_conflict"
    SAFETY = "safety_conflict"
    PREFERENCE = "preference_conflict"
    UNKNOWN = "unknown"

    @property
    def label_cn(self) -> str:
        return {
            "scope_conflict": "范围冲突",
            "evidence_conflict": "证据冲突",
            "implementation_conflict": "实现冲突",
            "review_conflict": "审查冲突",
            "safety_conflict": "安全冲突",
            "preference_conflict": "偏好冲突",
            "unknown": "未知冲突",
        }.get(self.value, self.value)


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def label_cn(self) -> str:
        return {"low": "低", "medium": "中", "high": "高", "critical": "严重"}.get(self.value, self.value)

    @property
    def requires_human(self) -> bool:
        return self in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL)


@dataclass
class ConflictRecord:
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    description_cn: str
    party_a: str  # role or context
    party_b: str
    source_refs: list[str]
    resolution_options: list[dict]  # [{option: str, risk_cn: str}]
    resolved: bool
    resolution_cn: str
    requires_human: bool
    created_at: str

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "conflict_type_label_cn": self.conflict_type.label_cn,
            "severity": self.severity.value,
            "severity_label_cn": self.severity.label_cn,
            "description_cn": self.description_cn,
            "party_a": self.party_a,
            "party_b": self.party_b,
            "source_refs": self.source_refs,
            "resolution_options": self.resolution_options,
            "resolved": self.resolved,
            "resolution_cn": self.resolution_cn,
            "requires_human": self.requires_human,
            "created_at": self.created_at,
        }


class ConflictResolutionService:

    def __init__(self) -> None:
        self._conflicts: dict[str, ConflictRecord] = {}

    def detect(
        self,
        conflict_type: str,
        description_cn: str,
        party_a: str,
        party_b: str,
        source_refs: list[str] | None = None,
    ) -> ConflictRecord:
        """Detect and classify a conflict. Returns a conflict record with
        proposed resolution options. Never auto-resolves."""
        try:
            ct = ConflictType(conflict_type)
        except ValueError:
            ct = ConflictType.UNKNOWN

        # Classify severity
        if ct == ConflictType.SAFETY:
            severity = ConflictSeverity.CRITICAL
        elif ct in (ConflictType.REVIEW, ConflictType.IMPLEMENTATION):
            severity = ConflictSeverity.HIGH
        elif ct == ConflictType.EVIDENCE:
            severity = ConflictSeverity.MEDIUM
        else:
            severity = ConflictSeverity.MEDIUM

        # Generate resolution options
        options = self._generate_options(ct, party_a, party_b)

        conflict = ConflictRecord(
            conflict_id=f"cf-{uuid.uuid4().hex[:8]}",
            conflict_type=ct,
            severity=severity,
            description_cn=description_cn,
            party_a=party_a,
            party_b=party_b,
            source_refs=source_refs or [],
            resolution_options=options,
            resolved=False,
            resolution_cn="",
            requires_human=severity.requires_human,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._conflicts[conflict.conflict_id] = conflict
        return conflict

    def _generate_options(self, ct: ConflictType, party_a: str, party_b: str) -> list[dict]:
        """Generate A/B/C resolution options based on conflict type."""
        base = []

        if ct == ConflictType.SAFETY:
            base = [
                {"option": "A", "label": "暂停所有操作，人工安全审查", "risk_cn": "项目暂停，但安全优先"},
                {"option": "B", "label": "降级安全要求，继续运行", "risk_cn": "可能引入安全漏洞，不推荐"},
                {"option": "C", "label": "隔离受影响模块，其他继续", "risk_cn": "操作复杂，可能遗漏关联影响"},
            ]
        elif ct == ConflictType.REVIEW:
            base = [
                {"option": "A", "label": "接受审查者判断，构建者修复", "risk_cn": "可能延长开发时间"},
                {"option": "B", "label": "请求第三方仲裁", "risk_cn": "引入额外延迟"},
                {"option": "C", "label": "降级问题等级，有条件通过", "risk_cn": "可能遗漏重要问题"},
            ]
        elif ct == ConflictType.EVIDENCE:
            base = [
                {"option": "A", "label": "补充缺失证据后重新评估", "risk_cn": "需要额外研究时间"},
                {"option": "B", "label": "接受现有证据，增加不确定性标注", "risk_cn": "决策基础不完整"},
                {"option": "C", "label": "缩小范围到有证据支持的部分", "risk_cn": "可能遗漏关键需求"},
            ]
        elif ct == ConflictType.IMPLEMENTATION:
            base = [
                {"option": "A", "label": "采用 Builder 实现，记录已知问题", "risk_cn": "已知问题需后续修复"},
                {"option": "B", "label": "回退到 Planner 重新设计", "risk_cn": "可能影响进度"},
                {"option": "C", "label": "合并两个方案的优势点", "risk_cn": "需要额外集成工作"},
            ]
        elif ct == ConflictType.SCOPE:
            base = [
                {"option": "A", "label": "缩小范围，只做共识部分", "risk_cn": "功能不完整"},
                {"option": "B", "label": "扩展范围，包含两方需求", "risk_cn": "资源需求增加"},
                {"option": "C", "label": "分阶段：先做 A 后做 B", "risk_cn": "交付周期延长"},
            ]
        else:
            base = [
                {"option": "A", "label": "人工介入决策", "risk_cn": "依赖人的判断"},
                {"option": "B", "label": "采纳 party_a 方案", "risk_cn": f"可能忽略 {party_b} 的关切"},
                {"option": "C", "label": "采纳 party_b 方案", "risk_cn": f"可能忽略 {party_a} 的关切"},
            ]

        return base

    def resolve(
        self,
        conflict_id: str,
        chosen_option: str,
        resolution_cn: str,
    ) -> Optional[ConflictRecord]:
        """Mark a conflict as resolved with chosen option. Does NOT auto-resolve
        high/critical conflicts — caller must check requires_human."""
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            return None
        if conflict.requires_human and not resolution_cn:
            return None  # High risk requires explicit resolution
        conflict.resolved = True
        conflict.resolution_cn = f"选项 {chosen_option}：{resolution_cn}"
        return conflict

    def list_conflicts(self, resolved: bool | None = None) -> list[ConflictRecord]:
        results = list(self._conflicts.values())
        if resolved is not None:
            results = [c for c in results if c.resolved == resolved]
        return results

    def get_conflict(self, conflict_id: str) -> Optional[ConflictRecord]:
        return self._conflicts.get(conflict_id)
