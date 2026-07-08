"""Failure classifier. Explains and suggests next steps, never auto-fixes."""
from __future__ import annotations

# ── Failure categories ──
CATEGORIES = {
    "user_input": "用户输入问题",
    "permission_waiting": "权限等待",
    "tool_failure": "工具执行失败",
    "test_failure": "测试失败",
    "network_failure": "网络失败",
    "code_quality": "代码质量失败",
    "security_block": "安全阻断",
    "unknown": "未知失败",
}

# ── Category metadata ──
_CATEGORY_META: dict[str, dict] = {
    "user_input": {
        "label": "用户输入问题",
        "suggestion": "请检查输入的目标描述是否清晰、是否有拼写错误、是否缺少必要的上下文。",
        "retryable": True,
        "auto_fix_possible": False,
    },
    "permission_waiting": {
        "label": "权限等待",
        "suggestion": "操作正在等待 PermissionGate 审核。请在权限面板中批准或拒绝此请求。",
        "retryable": False,
        "auto_fix_possible": False,
    },
    "tool_failure": {
        "label": "工具执行失败",
        "suggestion": "工具返回了错误结果。请检查工具参数是否正确、目标文件是否存在、权限是否足够。",
        "retryable": True,
        "auto_fix_possible": False,
    },
    "test_failure": {
        "label": "测试失败",
        "suggestion": "自动化测试未通过。请查看测试输出，修复代码后重新运行。",
        "retryable": True,
        "auto_fix_possible": False,
    },
    "network_failure": {
        "label": "网络失败",
        "suggestion": "网络连接失败或超时。请检查网络/VPN/代理设置，稍后重试。",
        "retryable": True,
        "auto_fix_possible": False,
    },
    "code_quality": {
        "label": "代码质量失败",
        "suggestion": "代码质量检查未通过（lint/build/type check）。请修复质量问题后重新提交。",
        "retryable": True,
        "auto_fix_possible": False,
    },
    "security_block": {
        "label": "安全阻断",
        "suggestion": "操作被安全策略阻断。这包括：尝试执行危险命令、绕过 PermissionGate、访问未授权资源。请确认操作必要性后通过正规渠道申请。",
        "retryable": False,
        "auto_fix_possible": False,
    },
    "unknown": {
        "label": "未知失败",
        "suggestion": "发生了未分类的失败。请查看执行审计日志获取详细信息，或联系用户进行人工诊断。",
        "retryable": False,
        "auto_fix_possible": False,
    },
}

# ── Classification patterns ──
_PATTERNS: list[tuple[str, list[str]]] = [
    ("security_block", [
        "permission denied", "not authorized", "forbidden",
        "安全阻断", "拒绝访问", "不在白名单",
        "bypass", "绕过", "未经授权",
    ]),
    ("permission_waiting", [
        "waiting_permission", "pending_permission",
        "等待权限", "等待批准", "等待人工",
        "needs approval", "requires permission",
    ]),
    ("network_failure", [
        "connection refused", "timeout", "network",
        "dns", "resolve", "connect",
        "连接失败", "超时", "网络",
        "ConnectionError", "TimeoutError",
    ]),
    ("test_failure", [
        "test failed", "assertion", "assert",
        "pytest", "vitest", "unittest",
        "测试失败", "断言失败",
    ]),
    ("code_quality", [
        "lint", "type error", "typeerror",
        "build failed", "compilation",
        "eslint", "mypy", "tsc",
        "质量门", "类型错误",
    ]),
    ("tool_failure", [
        "tool error", "command failed", "exit code",
        "execution failed", "execution_error",
        "工具执行", "执行失败",
        "ToolError", "ExecutionError",
    ]),
    ("user_input", [
        "invalid input", "bad request", "validation",
        "missing", "required", "cannot be empty",
        "输入无效", "缺少参数", "格式错误",
        "ValueError", "ValidationError",
    ]),
]


class FailureClassifier:
    """Classifies execution failures and provides Chinese explanations.
    Never auto-fixes or retries. Works with evidence/audit/task closure."""

    @staticmethod
    def categories() -> dict:
        """Return all failure categories with metadata."""
        result: dict[str, dict] = {}
        for code, meta in sorted(_CATEGORY_META.items()):
            result[code] = dict(meta)
        return result

    @staticmethod
    def classify(error_text: str, context: str = "") -> dict:
        """Classify an error message into a failure category.
        Returns category with Chinese label, suggestion, and retry guidance."""
        error_lower = error_text.lower()
        context_lower = context.lower() if context else ""

        for category, keywords in _PATTERNS:
            for kw in keywords:
                if kw.lower() in error_lower or kw.lower() in context_lower:
                    meta = _CATEGORY_META[category]
                    return {
                        "category": category,
                        "label": meta["label"],
                        "suggestion": meta["suggestion"],
                        "retryable": meta["retryable"],
                        "auto_fix_possible": meta["auto_fix_possible"],
                        "error_summary": error_text[:200],
                        "context": context,
                    }

        # Default: unknown
        meta = _CATEGORY_META["unknown"]
        return {
            "category": "unknown",
            "label": meta["label"],
            "suggestion": meta["suggestion"],
            "retryable": meta["retryable"],
            "auto_fix_possible": meta["auto_fix_possible"],
            "error_summary": error_text[:200],
            "context": context,
        }

    @staticmethod
    def is_retryable(error_text: str, context: str = "") -> bool:
        """Quick check: can this failure be retried?"""
        return FailureClassifier.classify(error_text, context)["retryable"]
