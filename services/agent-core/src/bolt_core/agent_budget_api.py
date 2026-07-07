"""Agent Budget API router. Budget check endpoint, never auto-executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.agent_budget import AgentBudgetService, BudgetConfig, BudgetState


def create_agent_budget_router() -> APIRouter:
    """Create router for agent budget operations.

    The check endpoint evaluates current consumption against budget limits.
    It NEVER auto-increases budget or auto-continues after blocking.
    """
    router = APIRouter(tags=["agent-budget"])
    service = AgentBudgetService()

    @router.post("/agent-budget/check")
    def check_budget(payload: dict) -> dict:
        """Check if current agent state is within configured budget.

        Accepts config (limits) and state (current consumption).
        Returns allowed=true if all dimensions are within limits,
        or allowed=false with Chinese blocking explanation.
        """
        try:
            config = BudgetConfig.from_dict(payload.get("config"))
            state = BudgetState(
                steps_used=int(payload.get("state", {}).get("steps_used", 0)),
                tool_calls_used=int(payload.get("state", {}).get("tool_calls_used", 0)),
                elapsed_seconds=float(payload.get("state", {}).get("elapsed_seconds", 0)),
                context_tokens_used=int(payload.get("state", {}).get("context_tokens_used", 0)),
            )
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"预算参数无效：{e}")

        result = service.check(config, state)
        return result.to_dict()

    @router.post("/agent-budget/check-single")
    def check_single_dimension(payload: dict) -> dict:
        """Check a single budget dimension."""
        dimension = str(payload.get("dimension", ""))
        if not dimension:
            raise HTTPException(status_code=400, detail="dimension 不能为空。")
        try:
            used = float(payload.get("used", 0))
            limit = float(payload.get("limit", 1))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="used 和 limit 必须为数字。")
        label = str(payload.get("label_cn", ""))
        result = service.check_single(dimension, used, limit, label)
        return result.to_dict()

    @router.get("/agent-budget/defaults")
    def get_defaults() -> dict:
        """Return the safe default budget configuration."""
        return BudgetConfig().to_dict()

    return router
