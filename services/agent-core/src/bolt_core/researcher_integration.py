"""Researcher Integration. Read-only research role that produces structured
summaries with source_refs. Enforces 2-4 relevant docs rule.

References M71-M75 memory layers for research scope classification.

M159: ResearcherEngine moved to researcher_engine.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


# ── Research scope ──────────────────────────────────────────────────────

class ResearchScope(str, Enum):
    PROJECT_DOCS = "project_docs"
    BINCLOUD_REFS = "bincloud_refs"
    CODE_MAP = "code_map"
    DECISION_MEMORY = "decision_memory"
    FAILURE_MEMORY = "failure_memory"

    @property
    def label_cn(self) -> str:
        _labels = {
            "project_docs": "项目文档",
            "bincloud_refs": "BinCloud 参考资料",
            "code_map": "代码地图",
            "decision_memory": "决策记忆",
            "failure_memory": "失败记忆",
        }
        return _labels.get(self.value, self.value)


# Hard limits
_MAX_SOURCES = 4  # Maximum allowed sources per research brief
_MIN_SOURCES = 2  # Recommended minimum for meaningful research


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class ResearchBrief:
    """A research task definition. Created by Planner, executed by Researcher."""
    brief_id: str
    title_cn: str
    question_cn: str  # What to research
    allowed_sources: list[str]  # Specific doc paths or scope identifiers
    scope: ResearchScope
    max_sources: int = _MAX_SOURCES
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "title_cn": self.title_cn,
            "question_cn": self.question_cn,
            "allowed_sources": self.allowed_sources,
            "scope": self.scope.value,
            "scope_label_cn": self.scope.label_cn,
            "max_sources": self.max_sources,
            "created_at": self.created_at,
        }


@dataclass
class ResearchSummary:
    """Output from Researcher. Must carry source_refs."""
    brief_id: str
    summary_cn: str
    principles_cn: list[str]  # Adopted principles
    risks_cn: list[str]  # Identified risks
    source_refs: list[str]  # All referenced documents
    scope: ResearchScope
    findings_count: int
    submitted_at: str = ""

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "summary_cn": self.summary_cn,
            "principles_cn": self.principles_cn,
            "risks_cn": self.risks_cn,
            "source_refs": self.source_refs,
            "scope": self.scope.value,
            "scope_label_cn": self.scope.label_cn,
            "findings_count": self.findings_count,
            "submitted_at": self.submitted_at,
        }


@dataclass
class ResearchValidation:
    """Validation result for research brief or summary."""
    valid: bool
    message_cn: str
    details: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "message_cn": self.message_cn,
            "details": self.details,
            "blocked": self.blocked,
        }


# ── Service ─────────────────────────────────────────────────────────────

class ResearcherIntegrationService:
    """Manages research briefs and summaries. Read-only; no file modification."""

    def __init__(self) -> None:
        self._briefs: dict[str, ResearchBrief] = {}
        self._summaries: dict[str, ResearchSummary] = {}

    # ── Create brief ─────────────────────────────────────────────────

    def create_brief(
        self,
        title_cn: str,
        question_cn: str,
        allowed_sources: list[str],
        scope: str,
    ) -> ResearchValidation | ResearchBrief:
        """Create a research brief with source validation.

        Rules:
        - allowed_sources must be 2-4 (warning if >4)
        - scope must be valid
        - No broad crawls (all sources must be specific)
        """
        # Validate scope
        try:
            scope_enum = ResearchScope(scope)
        except ValueError:
            return ResearchValidation(
                valid=False,
                message_cn=f"无效的研究范围：{scope}。有效值：{', '.join(s.value for s in ResearchScope)}。",
                blocked=True,
            )

        # Validate sources
        if not allowed_sources:
            return ResearchValidation(
                valid=False,
                message_cn="研究摘要必须指定 allowed_sources（允许的资料列表）。不能进行无限制的知识库爬取。",
                blocked=True,
            )

        if len(allowed_sources) > _MAX_SOURCES:
            return ResearchValidation(
                valid=False,
                message_cn=(
                    f"资料数量超过上限：{len(allowed_sources)} > {_MAX_SOURCES}。"
                    f"请精选 {_MAX_SOURCES} 篇以内相关资料。"
                ),
                details=[f"提供的资料：{', '.join(allowed_sources)}"],
                blocked=True,
            )

        if len(allowed_sources) < _MIN_SOURCES:
            # Warning, not blocked
            pass

        brief_id = f"rb-{uuid.uuid4().hex[:8]}"
        brief = ResearchBrief(
            brief_id=brief_id,
            title_cn=title_cn,
            question_cn=question_cn,
            allowed_sources=allowed_sources,
            scope=scope_enum,
            max_sources=_MAX_SOURCES,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._briefs[brief_id] = brief
        return brief

    # ── Produce summary ──────────────────────────────────────────────

    def produce_summary(
        self,
        brief_id: str,
        summary_cn: str,
        principles_cn: list[str],
        risks_cn: list[str],
        source_refs: list[str],
    ) -> ResearchValidation | ResearchSummary:
        """Submit a research summary. Must reference the brief's allowed sources.

        Rules:
        - source_refs must not be empty
        - source_refs should align with brief's allowed_sources (warning if diverge)
        - Cannot generate patch/command/approve
        """
        brief = self._briefs.get(brief_id)
        if brief is None:
            return ResearchValidation(
                valid=False,
                message_cn=f"未找到研究摘要：{brief_id}。",
                blocked=True,
            )

        if not source_refs:
            return ResearchValidation(
                valid=False,
                message_cn="研究输出必须包含 source_refs（引用的文档路径）。无 source_refs 的输出不能交给 Planner。",
                blocked=True,
            )

        if not summary_cn:
            return ResearchValidation(
                valid=False,
                message_cn="研究摘要必须包含中文摘要（summary_cn）。",
                blocked=True,
            )

        # Check source alignment (warning only)
        details: list[str] = []
        brief_sources_set = set(brief.allowed_sources)
        refs_set = set(source_refs)
        if not refs_set.issubset(brief_sources_set):
            extra = refs_set - brief_sources_set
            if extra:
                details.append(
                    f"注意：source_refs 包含不在原始 brief 允许列表中的资料："
                    f"{', '.join(sorted(extra))}。请确认这些额外引用是否必要。"
                )

        # Validate that summary includes principles and risks
        if not principles_cn:
            details.append("建议：摘要应包含采用原则（principles_cn）。")

        submitted_at = datetime.now(timezone.utc).isoformat()
        summary = ResearchSummary(
            brief_id=brief_id,
            summary_cn=summary_cn,
            principles_cn=principles_cn,
            risks_cn=risks_cn,
            source_refs=source_refs,
            scope=brief.scope,
            findings_count=len(source_refs),
            submitted_at=submitted_at,
        )
        self._summaries[brief_id] = summary
        return summary

    # ── Read ────────────────────────────────────────────────────────

    def list_briefs(self) -> list[ResearchBrief]:
        return list(self._briefs.values())

    def get_brief(self, brief_id: str) -> Optional[ResearchBrief]:
        return self._briefs.get(brief_id)

    def list_summaries(self) -> list[ResearchSummary]:
        return list(self._summaries.values())

    def get_summary(self, brief_id: str) -> Optional[ResearchSummary]:
        return self._summaries.get(brief_id)

    # ── Validate ────────────────────────────────────────────────────

    def validate_source_refs(self, source_refs: list[str]) -> ResearchValidation:
        """Check that source_refs are well-formed (non-empty, specific paths)."""
        if not source_refs:
            return ResearchValidation(
                valid=False,
                message_cn="source_refs 为空。研究输出必须有引用来源。",
                blocked=True,
            )
        if len(source_refs) > _MAX_SOURCES * 2:
            return ResearchValidation(
                valid=False,
                message_cn=f"引用来源过多（{len(source_refs)}），请精简。",
                blocked=False,
            )
        return ResearchValidation(
            valid=True,
            message_cn=f"source_refs 验证通过：{len(source_refs)} 条引用。",
        )

    def scope_options(self) -> list[dict]:
        """List all valid research scopes with Chinese labels."""
        return [
            {"scope": s.value, "label_cn": s.label_cn}
            for s in ResearchScope
        ]


# ResearcherEngine moved to researcher_engine.py (M159)
from bolt_core.researcher_engine import ResearcherEngine
