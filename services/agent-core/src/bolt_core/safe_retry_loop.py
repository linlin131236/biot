"""Safe retry loop. Controlled retry with safety boundaries, never auto-retries dangerous ops."""
from __future__ import annotations

from bolt_core.failure_classifier import FailureClassifier
from bolt_core.tool_selection_policy import DANGEROUS, SIDE_EFFECT, ToolSelectionPolicy

# ── Default limits ──
DEFAULT_MAX_RETRIES = 3

# ── Categories that are NEVER auto-retriable ──
NEVER_RETRY_CATEGORIES = {"security_block", "permission_waiting"}

# ── Tool classes that are NEVER auto-retriable ──
NEVER_RETRY_TOOL_CLASSES = {DANGEROUS}


class SafeRetryPolicy:
    """Determines retry eligibility based on failure classification and tool safety."""

    @staticmethod
    def assess(failure_category: str, tool_names: list[str] | None = None,
               attempt: int = 0, max_attempts: int = DEFAULT_MAX_RETRIES,
               reason: str = "") -> dict:
        """Assess whether a retry is allowed. Returns a detailed decision."""

        # Check category
        if failure_category in NEVER_RETRY_CATEGORIES:
            return {
                "allowed": False,
                "reason": f"失败类别 '{failure_category}' 禁止自动重试。需人工介入。",
                "category": failure_category,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "suggestion": "请人工诊断并修复后再试。",
            }

        # Check attempt count
        if attempt >= max_attempts:
            return {
                "allowed": False,
                "reason": f"已达到最大重试次数 ({max_attempts})。停止重试。",
                "category": failure_category,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "suggestion": f"已尝试 {max_attempts} 次，均未成功。请检查失败原因后人工处理。",
            }

        # Check tool safety
        if tool_names:
            for name in tool_names:
                info = ToolSelectionPolicy.classify(name)
                if info["class"] in NEVER_RETRY_TOOL_CLASSES:
                    return {
                        "allowed": False,
                        "reason": f"工具 '{name}' 为危险工具，禁止自动重试。",
                        "category": failure_category,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "suggestion": "危险操作不可自动重试，需由用户在 PermissionGate 中明确批准。",
                    }

        # Check if failure is retryable at all
        classifier_result = {"category": failure_category, "retryable": True}
        # Use the classifier's built-in knowledge
        if failure_category == "unknown":
            return {
                "allowed": False,
                "reason": "未知失败类别，不建议自动重试。",
                "category": failure_category,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "suggestion": "请先诊断失败原因，明确分类后再决定是否重试。",
            }

        return {
            "allowed": True,
            "reason": reason or "失败可重试，安全条件满足。",
            "category": failure_category,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "next_attempt": attempt + 1,
            "remaining": max_attempts - attempt - 1,
            "suggestion": f"第 {attempt + 1}/{max_attempts} 次重试。剩余 {max_attempts - attempt - 1} 次。",
        }


class SafeRetryLoop:
    """Tracks retry attempts for a specific operation. Enforces policy boundaries."""

    def __init__(self, max_attempts: int = DEFAULT_MAX_RETRIES) -> None:
        self._max_attempts = max_attempts
        self._history: list[dict] = []

    @property
    def attempts(self) -> int:
        return len(self._history)

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self._max_attempts

    def can_retry(self, failure_category: str, tool_names: list[str] | None = None) -> bool:
        """Check if another retry is allowed."""
        decision = SafeRetryPolicy.assess(
            failure_category, tool_names, self.attempts, self._max_attempts,
        )
        return decision["allowed"]

    def record_retry(self, failure_category: str, tool_names: list[str] | None = None,
                     error_text: str = "", reason: str = "") -> dict:
        """Record a retry attempt. Returns decision and updates history."""
        decision = SafeRetryPolicy.assess(
            failure_category, tool_names, self.attempts, self._max_attempts, reason,
        )
        entry = {
            "attempt": self.attempts + 1,
            "failure_category": failure_category,
            "error_text": error_text[:200],
            "allowed": decision["allowed"],
            "reason": decision["reason"],
            "timestamp": __import__("time").time(),
        }
        self._history.append(entry)
        decision["history"] = list(self._history)
        return decision

    def summary(self) -> dict:
        """Return summary of retry history."""
        return {
            "attempts": self.attempts,
            "max_attempts": self._max_attempts,
            "exhausted": self.exhausted,
            "history": list(self._history),
            "disclaimer": "安全重试循环仅记录和验证重试条件，实际执行需通过 PermissionGate 和人工确认。",
        }
