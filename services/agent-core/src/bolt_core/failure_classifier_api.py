"""Failure classifier API. Explains and suggests, never auto-fixes."""
from fastapi import APIRouter, HTTPException

from bolt_core.failure_classifier import FailureClassifier


def create_failure_classifier_router() -> APIRouter:
    router = APIRouter(tags=["failure"])

    @router.get("/failure/categories")
    def failure_categories() -> dict:
        """Return all failure categories with metadata."""
        return FailureClassifier.categories()

    @router.post("/failure/classify")
    def classify_failure(payload: dict) -> dict:
        """Classify an error message into a failure category."""
        error_text = str(payload.get("error", ""))
        if not error_text.strip():
            raise HTTPException(status_code=400, detail="error text is required")
        context = str(payload.get("context", ""))
        return FailureClassifier.classify(error_text.strip(), context.strip())

    @router.post("/failure/is-retryable")
    def is_retryable(payload: dict) -> dict:
        """Check if a failure can be retried."""
        error_text = str(payload.get("error", ""))
        if not error_text.strip():
            raise HTTPException(status_code=400, detail="error text is required")
        context = str(payload.get("context", ""))
        result = FailureClassifier.classify(error_text.strip(), context.strip())
        return {
            "retryable": result["retryable"],
            "category": result["category"],
            "label": result["label"],
            "suggestion": result["suggestion"],
        }

    return router
