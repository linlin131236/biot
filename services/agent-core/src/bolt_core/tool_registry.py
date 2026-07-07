"""Tool Registry. Unified registration, query, and management of tools.

Does NOT execute tools. All user-visible fields are Chinese.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ── Tool categories ──
CATEGORY_READ_ONLY = "read_only"
CATEGORY_SIDE_EFFECT = "side_effect"
CATEGORY_WRITE = "write"
CATEGORY_DANGEROUS = "dangerous"
CATEGORY_UNKNOWN = "unknown"

CATEGORIES = {CATEGORY_READ_ONLY, CATEGORY_SIDE_EFFECT, CATEGORY_WRITE, CATEGORY_DANGEROUS, CATEGORY_UNKNOWN}

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_READ_ONLY: "只读",
    CATEGORY_SIDE_EFFECT: "有副作用",
    CATEGORY_WRITE: "写入",
    CATEGORY_DANGEROUS: "危险",
    CATEGORY_UNKNOWN: "未知",
}

# ── Permission levels ──
PERM_NONE = "none"
PERM_READ = "read"
PERM_WRITE = "write"
PERM_EXECUTE = "execute"
PERM_DANGEROUS = "dangerous"

PERM_LABELS: dict[str, str] = {
    PERM_NONE: "无需权限",
    PERM_READ: "只读权限",
    PERM_WRITE: "写入权限",
    PERM_EXECUTE: "执行权限",
    PERM_DANGEROUS: "危险权限",
}

# ── Risk levels ──
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

RISK_LABELS: dict[str, str] = {
    RISK_LOW: "低",
    RISK_MEDIUM: "中",
    RISK_HIGH: "高",
    RISK_CRITICAL: "严重",
}


@dataclass(frozen=True)
class ToolDef:
    """Immutable tool definition. All user-visible fields in Chinese."""
    tool_id: str
    display_name: str
    category: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    permission_required: str = PERM_NONE
    allow_auto_run: bool = False
    risk_level: str = RISK_LOW

    def __post_init__(self):
        if not self.tool_id or not isinstance(self.tool_id, str):
            raise ValueError("tool_id 不能为空")
        if self.category not in CATEGORIES:
            raise ValueError(f"未知工具类别: {self.category}，合法值: {CATEGORIES}")
        if self.permission_required not in PERM_LABELS:
            raise ValueError(f"未知权限等级: {self.permission_required}，合法值: {list(PERM_LABELS)}")
        if self.risk_level not in RISK_LABELS:
            raise ValueError(f"未知风险等级: {self.risk_level}，合法值: {list(RISK_LABELS)}")

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "category": self.category,
            "category_label": CATEGORY_LABELS.get(self.category, "未知"),
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "permission_required": self.permission_required,
            "permission_label": PERM_LABELS.get(self.permission_required, "未知"),
            "allow_auto_run": self.allow_auto_run,
            "risk_level": self.risk_level,
            "risk_label": RISK_LABELS.get(self.risk_level, "未知"),
        }


class ToolRegistry:
    """统一工具注册表。只管理工具定义，不执行工具。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool_def: ToolDef) -> ToolDef:
        """注册一个工具。重复 ID 返回 ValueError。"""
        if tool_def.tool_id in self._tools:
            existing = self._tools[tool_def.tool_id]
            raise ValueError(
                f"工具 ID '{tool_def.tool_id}' 已注册（现有工具: {existing.display_name}）。"
                f" 如需更新请先调用 unregister()。"
            )
        self._tools[tool_def.tool_id] = tool_def
        return tool_def

    def get(self, tool_id: str) -> ToolDef | None:
        """按 ID 查询工具定义。"""
        return self._tools.get(tool_id)

    def list(self, category: str | None = None) -> list[ToolDef]:
        """列出所有已注册工具，可按 category 过滤。"""
        result = list(self._tools.values())
        if category:
            if category not in CATEGORIES:
                raise ValueError(f"未知工具类别: {category}")
            result = [t for t in result if t.category == category]
        result.sort(key=lambda t: t.tool_id)
        return result

    def unregister(self, tool_id: str) -> bool:
        """注销一个工具。返回 True 表示成功删除。"""
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False

    def summary(self) -> dict:
        """返回工具注册表的分类统计。"""
        counts: dict[str, int] = {}
        auto_run_counts: dict[str, int] = {}
        for t in self._tools.values():
            counts[t.category] = counts.get(t.category, 0) + 1
            if t.allow_auto_run:
                auto_run_counts[t.category] = auto_run_counts.get(t.category, 0) + 1
        return {
            "total": len(self._tools),
            "categories": {c: CATEGORY_LABELS[c] for c in sorted(CATEGORIES)},
            "counts_by_category": counts,
            "allow_auto_run_counts": auto_run_counts,
            "disclaimer": "工具注册表仅管理工具定义，不执行任何工具操作。",
        }

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools
