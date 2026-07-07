"""Safe retry loop API. Validates retry conditions, never auto-executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.safe_retry_loop import DEFAULT_MAX_RETRIES, SafeRetryLoop, SafeRetryPolicy


def create_safe_retry_loop_router() -> APIRouter:
    router = APIRouter(tags=["retry"])

    @router.post("/retry/assess")
    def assess_retry(payload: dict) -> dict:
        """Assess whether a retry is allowed for a given failure."""
        failure_category = str(payload.get("failure_category", ""))
        if not failure_category:
            raise HTTPException(status_code=400, detail="failure_category is required")
        tool_names = payload.get("tool_names")
        if tool_names is not None and not isinstance(tool_names, list):
            raise HTTPException(status_code=400, detail="tool_names must be a list")
        attempt = int(payload.get("attempt", 0))
        max_attempts = int(payload.get("max_attempts", DEFAULT_MAX_RETRIES))
        reason = str(payload.get("reason", ""))
        return SafeRetryPolicy.assess(
            failure_category, tool_names, attempt, max_attempts, reason,
        )

    @router.post("/retry/record")
    def record_retry(payload: dict) -> dict:
        """Record a retry attempt and return the decision."""
        failure_category = str(payload.get("failure_category", ""))
        if not failure_category:
            raise HTTPException(status_code=400, detail="failure_category is required")
        max_attempts = int(payload.get("max_attempts", DEFAULT_MAX_RETRIES))
        loop = SafeRetryLoop(max_attempts)
        # Pre-fill history if provided
        history = payload.get("history")
        if isinstance(history, list):
            for _ in history:
                loop._history.append({"attempt": len(loop._history) + 1, "pre_existing": True})
        return loop.record_retry(
            failure_category,
            tool_names=payload.get("tool_names"),
            error_text=str(payload.get("error_text", "")),
            reason=str(payload.get("reason", "")),
        )

    return router
