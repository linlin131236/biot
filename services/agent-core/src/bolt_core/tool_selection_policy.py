"""Tool selection policy. Classifies tools, does NOT execute them."""
from __future__ import annotations

from dataclasses import dataclass

# ── Tool classes ──
READ_ONLY = "read_only"
SIDE_EFFECT = "side_effect"
DANGEROUS = "dangerous"
UNKNOWN = "unknown"

TOOL_CLASSES = {READ_ONLY, SIDE_EFFECT, DANGEROUS, UNKNOWN}

CLASS_LABELS: dict[str, str] = {
    READ_ONLY: "只读工具",
    SIDE_EFFECT: "有副作用工具",
    DANGEROUS: "危险工具",
    UNKNOWN: "未知工具",
}

# ── Built-in tool registry ──
_BUILTIN_TOOLS: dict[str, dict] = {
    # ── 只读工具 ──
    "read_file":      {"class": READ_ONLY, "description": "读取文件内容"},
    "list_files":     {"class": READ_ONLY, "description": "列出目录文件"},
    "grep":           {"class": READ_ONLY, "description": "搜索文件内容"},
    "git_status":     {"class": READ_ONLY, "description": "查看 Git 工作区状态"},
    "git_log":        {"class": READ_ONLY, "description": "查看 Git 提交历史"},
    "git_diff":       {"class": READ_ONLY, "description": "查看文件差异"},
    "git_rev_parse":  {"class": READ_ONLY, "description": "解析 Git 引用"},
    "fetch_url":      {"class": READ_ONLY, "description": "获取 URL 内容"},
    "check_health":   {"class": READ_ONLY, "description": "健康检查"},
    # ── 有副作用工具 ──
    "write_file":     {"class": SIDE_EFFECT, "description": "写入文件"},
    "edit_file":      {"class": SIDE_EFFECT, "description": "编辑文件"},
    "git_commit":     {"class": SIDE_EFFECT, "description": "Git 提交"},
    "git_add":        {"class": SIDE_EFFECT, "description": "Git 暂存"},
    "npm_install":    {"class": SIDE_EFFECT, "description": "安装 npm 依赖"},
    "pip_install":    {"class": SIDE_EFFECT, "description": "安装 Python 包"},
    "mkdir":          {"class": SIDE_EFFECT, "description": "创建目录"},
    # ── 危险工具 ──
    "git_push":       {"class": DANGEROUS, "description": "Git 推送到远程"},
    "git_delete":     {"class": DANGEROUS, "description": "Git 删除分支/tag"},
    "rm_file":        {"class": DANGEROUS, "description": "删除文件"},
    "rm_dir":         {"class": DANGEROUS, "description": "删除目录"},
    "shell_exec":     {"class": DANGEROUS, "description": "执行 Shell 命令"},
    "release":        {"class": DANGEROUS, "description": "发布/打标签"},
    "tag":            {"class": DANGEROUS, "description": "创建 Git tag"},
    "delete":         {"class": DANGEROUS, "description": "删除资源"},
    "permission_approve": {"class": DANGEROUS, "description": "批准权限请求"},
}


@dataclass
class ToolSelectionResult:
    tool_name: str
    tool_class: str
    class_label: str
    allowed: bool
    requires_permission: bool
    warnings: list[str]
    suggestion: str


class ToolSelectionPolicy:
    """Classifies tools and validates selection. Never executes tools."""

    @staticmethod
    def classify(tool_name: str) -> dict:
        """Return the classification of a single tool."""
        info = _BUILTIN_TOOLS.get(tool_name)
        if info is None:
            return {"tool": tool_name, "class": UNKNOWN, "label": CLASS_LABELS[UNKNOWN],
                    "description": "未知工具，不在注册表中"}
        return {"tool": tool_name, "class": info["class"], "label": CLASS_LABELS[info["class"]],
                "description": info["description"]}

    @staticmethod
    def list_tools(tool_class: str | None = None) -> list[dict]:
        """List all registered tools, optionally filtered by class."""
        result = []
        for name, info in sorted(_BUILTIN_TOOLS.items()):
            if tool_class and info["class"] != tool_class:
                continue
            result.append({
                "name": name, "class": info["class"],
                "label": CLASS_LABELS[info["class"]],
                "description": info["description"],
            })
        return result

    @staticmethod
    def summary() -> dict:
        """Return a summary of tool classes and counts."""
        counts: dict[str, int] = {}
        for info in _BUILTIN_TOOLS.values():
            cls = info["class"]
            counts[cls] = counts.get(cls, 0) + 1
        return {
            "classes": {c: CLASS_LABELS[c] for c in sorted(TOOL_CLASSES)},
            "counts": counts,
            "total": sum(counts.values()),
        }

    @staticmethod
    def select(tool_names: list[str], reason: str = "") -> dict:
        """Validate a tool selection list. Returns per-tool results with
        overall allowed/requires_permission flags."""
        results: list[dict] = []
        any_disallowed = False
        any_requires_permission = False

        for name in tool_names:
            info = _BUILTIN_TOOLS.get(name)
            if info is None:
                results.append({
                    "tool": name, "class": UNKNOWN, "label": CLASS_LABELS[UNKNOWN],
                    "allowed": False, "requires_permission": False,
                    "warnings": ["未知工具，不在注册表中。拒绝执行。"],
                    "suggestion": "请使用注册表内的工具或先注册此工具。",
                })
                any_disallowed = True
                continue

            cls = info["class"]
            allowed = cls != UNKNOWN
            requires_permission = cls in (SIDE_EFFECT, DANGEROUS)
            warnings: list[str] = []
            suggestion = ""

            if cls == DANGEROUS:
                warnings.append("危险工具：需要爸爸在 PermissionGate 中明确批准后才可执行。")
                suggestion = "请通过 PermissionGate 人工审批后执行。"
            elif cls == SIDE_EFFECT:
                warnings.append("有副作用工具：将修改文件或状态，需进入执行队列等待人工确认。")
                suggestion = "将加入执行队列，等待人工确认后执行。"

            results.append({
                "tool": name, "class": cls, "label": CLASS_LABELS[cls],
                "allowed": allowed, "requires_permission": requires_permission,
                "warnings": warnings, "suggestion": suggestion,
            })
            if requires_permission:
                any_requires_permission = True

        return {
            "results": results,
            "all_allowed": not any_disallowed,
            "any_requires_permission": any_requires_permission,
            "reason": reason,
            "disclaimer": "工具选择策略仅判断工具分类和权限需求，不执行任何工具操作。",
        }
