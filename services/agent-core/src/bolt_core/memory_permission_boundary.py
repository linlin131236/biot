"""Memory Permission Boundary. 7-tier permission classification for memory.

Permission tiers:
- public_project: public project info, readable
- project_internal: internal docs, readable with source_refs
- user_preference: user prefs, write needs explicit source
- sensitive: sensitive content, block or redact
- secret: forbidden to save/display
- execution_evidence: display redacted summary only
- unknown: conservative block by default

Never auto-approves memory writes. Never allows secrets into long-term memory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PermissionTier(str, Enum):
    PUBLIC_PROJECT = "public_project"
    PROJECT_INTERNAL = "project_internal"
    USER_PREFERENCE = "user_preference"
    SENSITIVE = "sensitive"
    SECRET = "secret"
    EXECUTION_EVIDENCE = "execution_evidence"
    UNKNOWN = "unknown"


_TIER_LABELS: dict[PermissionTier, str] = {
    PermissionTier.PUBLIC_PROJECT: "项目公开信息",
    PermissionTier.PROJECT_INTERNAL: "项目内部文档",
    PermissionTier.USER_PREFERENCE: "用户偏好",
    PermissionTier.SENSITIVE: "敏感内容",
    PermissionTier.SECRET: "机密信息",
    PermissionTier.EXECUTION_EVIDENCE: "执行证据",
    PermissionTier.UNKNOWN: "未知",
}

_TIER_READABLE: dict[PermissionTier, bool] = {
    PermissionTier.PUBLIC_PROJECT: True,
    PermissionTier.PROJECT_INTERNAL: True,
    PermissionTier.USER_PREFERENCE: True,
    PermissionTier.SENSITIVE: False,
    PermissionTier.SECRET: False,
    PermissionTier.EXECUTION_EVIDENCE: False,
    PermissionTier.UNKNOWN: False,
}

_TIER_WRITABLE: dict[PermissionTier, bool] = {
    PermissionTier.PUBLIC_PROJECT: False,
    PermissionTier.PROJECT_INTERNAL: False,
    PermissionTier.USER_PREFERENCE: True,
    PermissionTier.SENSITIVE: False,
    PermissionTier.SECRET: False,
    PermissionTier.EXECUTION_EVIDENCE: False,
    PermissionTier.UNKNOWN: False,
}

_TIER_DISPLAYABLE: dict[PermissionTier, bool] = {
    PermissionTier.PUBLIC_PROJECT: True,
    PermissionTier.PROJECT_INTERNAL: True,
    PermissionTier.USER_PREFERENCE: True,
    PermissionTier.SENSITIVE: False,
    PermissionTier.SECRET: False,
    PermissionTier.EXECUTION_EVIDENCE: False,
    PermissionTier.UNKNOWN: False,
}

# ── Secret patterns ────────────────────────────────────────────────────
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
    (r'sk-ant-[a-zA-Z0-9_-]{20,}', "Anthropic API Key"),
    (r'AKIA[A-Z0-9]{16}', "AWS Access Key"),
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "RSA Private Key"),
    (r'-----BEGIN\s+CERTIFICATE-----', "Certificate"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
    (r'xox[bpras]-[a-zA-Z0-9-]+', "Slack Token"),
    (r'eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{0,}', "JWT Token"),
    (r'token\s*[:=]\s*[a-zA-Z0-9_-]{20,}', "Generic Token Assignment"),
]

_SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r'(?:password|passwd|pwd)\s*[:=]\s*\S{3,}', "密码"),
    (r'(?:email|mail)\s*[:=]\s*\S+@\S+', "邮箱"),
    (r'(?:phone|tel|mobile)\s*[:=]\s*[\d\-+]{7,}', "电话"),
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*\S{10,}', "API Key"),
    (r'(?:secret|private)\s*[:=]\s*\S{3,}', "Secret 字段"),
]


@dataclass(frozen=True)
class PermissionDecision:
    """Result of memory permission classification."""
    tier: PermissionTier
    tier_label: str
    can_read: bool
    can_write: bool
    can_display: bool
    explanation_cn: str
    redacted_content: Optional[str]
    detected_patterns: list[str]

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "tier_label": self.tier_label,
            "can_read": self.can_read,
            "can_write": self.can_write,
            "can_display": self.can_display,
            "explanation_cn": self.explanation_cn,
            "redacted_content": self.redacted_content,
            "detected_patterns": self.detected_patterns,
        }


class MemoryPermissionBoundary:
    """Classifies memory content into permission tiers.

    Determines read/write/display permission for each memory item.
    Redacts sensitive values. Blocks secrets from long-term memory.
    NEVER auto-approves memory writes.
    """

    def classify(self, content: str, source: str = "") -> PermissionDecision:
        """Classify content into a permission tier and decide permissions."""
        detected: list[str] = []

        # Check for secrets first (highest priority)
        for pattern, label in _SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                detected.append(label)

        if detected:
            redacted = self._redact(content)
            return PermissionDecision(
                tier=PermissionTier.SECRET,
                tier_label=_TIER_LABELS[PermissionTier.SECRET],
                can_read=False,
                can_write=False,
                can_display=False,
                explanation_cn=f"检测到机密信息（{', '.join(detected)}）。机密信息禁止保存和展示，已执行脱敏处理。",
                redacted_content=redacted,
                detected_patterns=detected,
            )

        # Check for sensitive patterns
        detected_sensitive: list[str] = []
        for pattern, label in _SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                detected_sensitive.append(label)

        if detected_sensitive:
            redacted = self._redact(content)
            return PermissionDecision(
                tier=PermissionTier.SENSITIVE,
                tier_label=_TIER_LABELS[PermissionTier.SENSITIVE],
                can_read=False,
                can_write=False,
                can_display=False,
                explanation_cn=f"检测到敏感内容（{', '.join(detected_sensitive)}）。敏感内容不可直接展示，已脱敏。如需写入，需明确 source_refs。",
                redacted_content=redacted,
                detected_patterns=detected_sensitive,
            )

        # Check for execution evidence
        if self._is_execution_evidence(content, source):
            return PermissionDecision(
                tier=PermissionTier.EXECUTION_EVIDENCE,
                tier_label=_TIER_LABELS[PermissionTier.EXECUTION_EVIDENCE],
                can_read=False,
                can_write=False,
                can_display=False,
                explanation_cn="执行证据只能展示脱敏摘要。完整证据请通过审计渠道查看。",
                redacted_content=self._summarize_evidence(content),
                detected_patterns=[],
            )

        # Check for user preference
        if self._is_user_preference(content, source):
            return PermissionDecision(
                tier=PermissionTier.USER_PREFERENCE,
                tier_label=_TIER_LABELS[PermissionTier.USER_PREFERENCE],
                can_read=True,
                can_write=True,
                can_display=True,
                explanation_cn="用户偏好内容。可读取和展示。写入需要明确 source_refs 和用户确认。",
                redacted_content=None,
                detected_patterns=[],
            )

        # Check for project internal
        if self._is_project_internal(content, source):
            return PermissionDecision(
                tier=PermissionTier.PROJECT_INTERNAL,
                tier_label=_TIER_LABELS[PermissionTier.PROJECT_INTERNAL],
                can_read=True,
                can_write=False,
                can_display=True,
                explanation_cn="项目内部文档。可读取和展示，但需附 source_refs。不可自动写入。",
                redacted_content=None,
                detected_patterns=[],
            )

        # Default: public project info
        return PermissionDecision(
            tier=PermissionTier.PUBLIC_PROJECT,
            tier_label=_TIER_LABELS[PermissionTier.PUBLIC_PROJECT],
            can_read=True,
            can_write=False,
            can_display=True,
            explanation_cn="项目公开信息。可自由读取和展示。",
            redacted_content=None,
            detected_patterns=[],
        )

    def classify_unknown(self, content: str) -> PermissionDecision:
        """Conservative classification for unknown content. Blocks by default."""
        return PermissionDecision(
            tier=PermissionTier.UNKNOWN,
            tier_label=_TIER_LABELS[PermissionTier.UNKNOWN],
            can_read=False,
            can_write=False,
            can_display=False,
            explanation_cn="未知类型内容，按保守策略阻断。请明确内容来源和用途后重新评估。",
            redacted_content="[内容已阻断：未知类型]",
            detected_patterns=[],
        )

    def _redact(self, content: str) -> str:
        """Redact secret/sensitive values from content."""
        result = content
        for pattern, label in _SECRET_PATTERNS:
            result = re.sub(pattern, f'[{label}：已脱敏]', result, flags=re.IGNORECASE)
        for pattern, label in _SENSITIVE_PATTERNS:
            result = re.sub(pattern, f'[{label}：已脱敏]', result, flags=re.IGNORECASE)
        return result

    def _summarize_evidence(self, content: str) -> str:
        """Produce a redacted summary of execution evidence."""
        if len(content) > 200:
            return f"[执行证据摘要：{content[:197]}...]"
        return f"[执行证据摘要：{content}]"

    @staticmethod
    def _is_execution_evidence(content: str, source: str) -> bool:
        """Detect execution evidence patterns."""
        lower = (content + source).lower()
        indicators = [
            "execution_audit", "trace", "tool_result",
            "执行审计", "工具结果", "shell output",
            "execution output", "exit code",
        ]
        return any(ind in lower for ind in indicators)

    @staticmethod
    def _is_user_preference(content: str, source: str) -> bool:
        """Detect user preference patterns."""
        lower = (content + source).lower()
        indicators = [
            "preference", "偏好", "爸爸",
            "用户偏好", "user_preference",
        ]
        return any(ind in lower for ind in indicators)

    @staticmethod
    def _is_project_internal(content: str, source: str) -> bool:
        """Detect project internal document patterns."""
        lower = (content + source).lower()
        indicators = [
            "docs/", "decision", "review gate",
            "project-state", "milestone",
        ]
        return any(ind in lower for ind in indicators)

    def should_block_memory_write(self, content: str, source: str = "") -> tuple[bool, str]:
        """Quick check: should this content be blocked from memory write?

        Returns (should_block, reason_cn).
        """
        decision = self.classify(content, source)
        if decision.tier in (PermissionTier.SECRET, PermissionTier.SENSITIVE):
            return True, decision.explanation_cn
        if decision.tier == PermissionTier.UNKNOWN:
            return True, "未知类型内容，默认阻断。请提供明确来源后重新评估。"
        if decision.tier == PermissionTier.USER_PREFERENCE:
            if not source:
                return True, "用户偏好写入需要明确 source_refs。当前未提供来源。"
            return False, ""
        return False, ""
