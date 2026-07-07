"""Agent Budget Service. Gatekeeper for long-running agent tasks.

Checks four dimensions before allowing execution:
- max_steps: loop iteration limit
- max_tool_calls: tool invocation limit
- max_runtime_seconds: wall-clock time limit
- max_context_tokens: context token budget

Safety invariants:
- NEVER auto-increases budget
- NEVER auto-continues after blocking
- Missing budget → safe conservative defaults
- All blocking messages in Chinese
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Budget Model ──────────────────────────────────────────────────────

class BudgetDimension(str, Enum):
    STEPS = "steps"
    TOOL_CALLS = "tool_calls"
    RUNTIME = "runtime"
    CONTEXT_TOKENS = "context_tokens"


# Safe conservative defaults when budget is not specified
_DEFAULT_MAX_STEPS = 50
_DEFAULT_MAX_TOOL_CALLS = 100
_DEFAULT_MAX_RUNTIME_SECONDS = 1800  # 30 minutes
_DEFAULT_MAX_CONTEXT_TOKENS = 8000


@dataclass(frozen=True)
class BudgetConfig:
    """Budget limits for an agent run. All fields optional — missing = safe default."""
    max_steps: int = _DEFAULT_MAX_STEPS
    max_tool_calls: int = _DEFAULT_MAX_TOOL_CALLS
    max_runtime_seconds: int = _DEFAULT_MAX_RUNTIME_SECONDS
    max_context_tokens: int = _DEFAULT_MAX_CONTEXT_TOKENS

    def to_dict(self) -> dict:
        return {
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "max_runtime_seconds": self.max_runtime_seconds,
            "max_context_tokens": self.max_context_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> BudgetConfig:
        if not d:
            return cls()
        return cls(
            max_steps=int(d.get("max_steps", _DEFAULT_MAX_STEPS)),
            max_tool_calls=int(d.get("max_tool_calls", _DEFAULT_MAX_TOOL_CALLS)),
            max_runtime_seconds=int(d.get("max_runtime_seconds", _DEFAULT_MAX_RUNTIME_SECONDS)),
            max_context_tokens=int(d.get("max_context_tokens", _DEFAULT_MAX_CONTEXT_TOKENS)),
        )


@dataclass(frozen=True)
class BudgetState:
    """Current consumption state for a run."""
    steps_used: int = 0
    tool_calls_used: int = 0
    elapsed_seconds: float = 0.0
    context_tokens_used: int = 0

    def to_dict(self) -> dict:
        return {
            "steps_used": self.steps_used,
            "tool_calls_used": self.tool_calls_used,
            "elapsed_seconds": self.elapsed_seconds,
            "context_tokens_used": self.context_tokens_used,
        }


@dataclass(frozen=True)
class BudgetResult:
    """Result of a budget check. allowed=True means within budget on all dimensions."""
    allowed: bool
    dimension: str  # which dimension triggered block (empty if allowed)
    explanation: str  # Chinese explanation
    suggestion: str  # Chinese next-step suggestion
    config: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "dimension": self.dimension,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "config": self.config,
            "state": self.state,
        }


# ── Service ───────────────────────────────────────────────────────────

class AgentBudgetService:
    """Budget gatekeeper. Checks consumption against limits.

    Does NOT auto-increase budget. Does NOT auto-continue after blocking.
    Callers must pass current consumption state; this service only judges.
    """

    def check(self, config: BudgetConfig, state: BudgetState) -> BudgetResult:
        """Check all four budget dimensions. Returns blocked on first violation."""
        cfg = config.to_dict()
        st = state.to_dict()

        # 1. Steps
        if state.steps_used >= config.max_steps:
            return BudgetResult(
                allowed=False,
                dimension="steps",
                explanation=(
                    f"已达到步数上限。已使用 {state.steps_used} 步，"
                    f"上限为 {config.max_steps} 步。"
                ),
                suggestion=(
                    "建议缩小任务范围、拆分为子任务，"
                    "或由人工确认后提高步数上限后重新执行。"
                ),
                config=cfg,
                state=st,
            )

        # 2. Tool calls
        if state.tool_calls_used >= config.max_tool_calls:
            return BudgetResult(
                allowed=False,
                dimension="tool_calls",
                explanation=(
                    f"已达到工具调用次数上限。已调用 {state.tool_calls_used} 次，"
                    f"上限为 {config.max_tool_calls} 次。"
                ),
                suggestion=(
                    "建议检查是否存在工具调用死循环，"
                    "或由人工确认后提高工具调用上限。"
                ),
                config=cfg,
                state=st,
            )

        # 3. Runtime
        if state.elapsed_seconds >= config.max_runtime_seconds:
            return BudgetResult(
                allowed=False,
                dimension="runtime",
                explanation=(
                    f"已达到运行时间上限。已运行 {state.elapsed_seconds:.0f} 秒，"
                    f"上限为 {config.max_runtime_seconds} 秒"
                    f"（约 {config.max_runtime_seconds / 60:.0f} 分钟）。"
                ),
                suggestion=(
                    "建议将任务拆分为更小的子任务分批执行，"
                    "或由人工确认后延长运行时间上限。"
                ),
                config=cfg,
                state=st,
            )

        # 4. Context tokens
        if state.context_tokens_used >= config.max_context_tokens:
            return BudgetResult(
                allowed=False,
                dimension="context_tokens",
                explanation=(
                    f"已达到上下文 token 上限。已使用 {state.context_tokens_used} tokens，"
                    f"上限为 {config.max_context_tokens} tokens。"
                ),
                suggestion=(
                    "建议进行上下文压缩或清理历史对话，"
                    "或由人工确认后提高 token 上限。"
                ),
                config=cfg,
                state=st,
            )

        # All checks passed
        return BudgetResult(
            allowed=True,
            dimension="",
            explanation="预算检查通过，所有维度均在限制范围内。",
            suggestion="可以继续执行下一步。",
            config=cfg,
            state=st,
        )

    def check_single(self, dimension: str, used: float, limit: float,
                     label_cn: str = "") -> BudgetResult:
        """Check a single dimension against its limit.

        Returns allowed=True if under limit, False with Chinese explanation if over.
        """
        if used >= limit:
            return BudgetResult(
                allowed=False,
                dimension=dimension,
                explanation=(
                    f"{label_cn or dimension}已达上限。"
                    f"已使用 {used}，上限为 {limit}。"
                ),
                suggestion="请由人工确认后提高上限，或调整任务范围。",
                config={dimension: limit},
                state={dimension: used},
            )
        return BudgetResult(
            allowed=True,
            dimension=dimension,
            explanation=f"{label_cn or dimension}在预算范围内。",
            suggestion="可以继续。",
            config={dimension: limit},
            state={dimension: used},
        )
