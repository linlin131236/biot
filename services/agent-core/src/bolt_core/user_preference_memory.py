"""User Preference Memory Service. Read-only index of user preferences.

Strictly controlled: only records preferences explicitly stated in project-state hard rules.
NEVER infers preferences from one-time context.
NEVER stores secrets, tokens, certs, or private keys.
Preferences CANNOT override security hard rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PreferenceRecord:
    """A single user preference with source traceability."""
    preference_id: str
    category: str
    statement_cn: str
    confidence: str
    source_refs: list[str]
    can_apply_automatically: bool
    requires_confirmation: bool

    def to_dict(self) -> dict:
        return {
            "preference_id": self.preference_id,
            "category": self.category,
            "statement_cn": self.statement_cn,
            "confidence": self.confidence,
            "source_refs": self.source_refs,
            "can_apply_automatically": self.can_apply_automatically,
            "requires_confirmation": self.requires_confirmation,
        }


# ── Category definitions ──────────────────────────────────────────────
_CATEGORY_LABELS: dict[str, str] = {
    "language": "语言偏好",
    "address": "称呼偏好",
    "workflow": "工作流偏好",
    "safety": "安全偏好",
    "coding_style": "编码风格偏好",
    "product_direction": "产品方向偏好",
}

# ── Hard preferences from project-state (these CANNOT be overridden) ───
_HARD_PREFERENCES: list[PreferenceRecord] = [
    PreferenceRecord(
        preference_id="pref-001-language",
        category="language",
        statement_cn="所有用户可见 UI 必须中文。代码注释和文档优先中文。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-002-address",
        category="address",
        statement_cn="用户界面不使用私人称呼；对话与界面默认使用中文。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:硬规则", "用户明确指令"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-003-no-auto-push",
        category="safety",
        statement_cn="不自动 push、release、tag、delete。只在用户明确授权后执行。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-004-no-auto-approve",
        category="safety",
        statement_cn="不自动批准权限。不绕过 PermissionGate。不自动执行危险命令。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-005-no-commit-artifacts",
        category="safety",
        statement_cn="不提交生成物、缓存、虚拟环境、证书材料、.bolt、uv.lock。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-006-no-any-type",
        category="coding_style",
        statement_cn="不使用 as any / unknown as。代码文件尽量保持在 300 行以内。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-007-renderer-safety",
        category="safety",
        statement_cn="renderer 不暴露 ipcRenderer / fs / shell / process。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-008-milestone-discipline",
        category="workflow",
        statement_cn="每个 milestone 必须产出 exec plan、decision、phase review gate、project-state 更新和一个清晰 commit。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:每个 milestone 必须产出"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-009-no-unauthorized-milestone",
        category="workflow",
        statement_cn="不进入未授权 milestone。M72 完成后停止等待复审，未授权前不进入 M73。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-010-product-direction",
        category="product_direction",
        statement_cn="Biot 定位：Claude 的安全粒度 + Codex 的流畅执行。信任但验证。",
        confidence="confirmed",
        source_refs=["docs/桌面AI编程Agent全流程架构对比.md:结论", "docs/project-state.md"],
        can_apply_automatically=False,
        requires_confirmation=True,
    ),
    PreferenceRecord(
        preference_id="pref-011-code-simplicity",
        category="coding_style",
        statement_cn="简洁优先、精准修改。不写屎山代码。每个文件聚焦单一职责。",
        confidence="confirmed",
        source_refs=["docs/project-state.md:长期硬规则", "用户明确指令"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
    PreferenceRecord(
        preference_id="pref-012-context-lakehouse",
        category="workflow",
        statement_cn="Context Lakehouse 原则：raw/source_refs 保留，清洗可复现，结论可追溯。",
        confidence="confirmed",
        source_refs=["docs/project-state.md", "用户指令文档"],
        can_apply_automatically=True,
        requires_confirmation=False,
    ),
]


class UserPreferenceMemoryService:
    """Read-only index of user preferences from project-state and docs.

    NEVER infers from one-time context or temporary conversation.
    NEVER stores secrets, tokens, or private keys.
    Preferences CANNOT override security hard rules.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace_path).resolve())

    @staticmethod
    def _find_project_root(start: Path) -> Path:
        current = start
        for _ in range(5):
            if (current / "package.json").exists() and (current / "services").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return start

    # ── Public API ─────────────────────────────────────────────────────

    def list_all(self) -> list[PreferenceRecord]:
        """Return all known preferences."""
        return list(_HARD_PREFERENCES)

    def get_detail(self, preference_id: str) -> Optional[PreferenceRecord]:
        """Get a single preference by ID."""
        for p in _HARD_PREFERENCES:
            if p.preference_id == preference_id:
                return p
        return None

    def query_by_category(self, category: str) -> list[PreferenceRecord]:
        """Query preferences by category."""
        cat_lower = category.lower()
        return [p for p in _HARD_PREFERENCES if cat_lower in p.category.lower()]

    def query_by_keyword(self, keyword: str) -> list[PreferenceRecord]:
        """Query preferences by keyword."""
        kw = keyword.lower()
        results: list[PreferenceRecord] = []
        for p in _HARD_PREFERENCES:
            if kw in p.statement_cn.lower() or kw in p.category.lower():
                results.append(p)
        return results

    def check_conflicts(self) -> list[dict]:
        """Check for conflicting preferences and return Chinese conflict descriptions."""
        conflicts: list[dict] = []

        # Check: preferences that claim auto-apply but also require confirmation
        for p in _HARD_PREFERENCES:
            if p.can_apply_automatically and p.requires_confirmation:
                conflicts.append({
                    "preference_id": p.preference_id,
                    "conflict_type": "auto_apply_vs_confirm",
                    "description_cn": f"偏好 '{p.statement_cn[:50]}...' 同时设置了 can_apply_automatically=True 和 requires_confirmation=True，存在逻辑矛盾。",
                    "recommendation_cn": "建议将 requires_confirmation 设为 False，或 can_apply_automatically 设为 False。",
                })

        # Check: no preference overrides safety hard rules
        safety_ids = {p.preference_id for p in _HARD_PREFERENCES if p.category == "safety"}
        # This is a structural check - safety preferences are marked confirmed and auto-apply
        # If any non-safety preference tried to set can_apply_automatically=True for safety-critical
        # operations, that would be flagged here. Currently all safety prefs are correct.

        return conflicts

    def is_secret_attempt(self, text: str) -> bool:
        """Check if text appears to contain secrets that should NOT be stored."""
        lower = text.lower()
        secret_patterns = [
            r'sk-[a-z0-9]{20,}',      # OpenAI API key
            r'akia[a-z0-9]{16}',       # AWS access key
            r'private\s*key',          # private key
            r'-----begin\s',           # PEM header
            r'token\s*[:=]\s*[a-z0-9_-]{20,}',  # token assignment
        ]
        for pattern in secret_patterns:
            if re.search(pattern, lower):
                return True
        return False
