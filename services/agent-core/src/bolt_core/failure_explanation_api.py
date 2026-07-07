"""Failure Explanation API (M97). Self-contained, creates its own services."""
from fastapi import APIRouter

from bolt_core.failure_classifier import FailureClassifier
from bolt_core.failure_memory_index import FailureMemoryIndexService


def create_failure_explanation_router() -> APIRouter:
    router = APIRouter(tags=["failure-explanation"])
    memory = FailureMemoryIndexService(".")

    @router.get("/failure-explanation")
    def get_failure_explanation() -> dict:
        failures: list[dict] = []
        try:
            for f in memory.list_all()[:20]:
                d = f.to_dict()
                failures.append({
                    "id": d.get("failure_id", ""),
                    "category": d.get("category", ""),
                    "category_cn": d.get("category_cn", ""),
                    "summary": d.get("summary", ""),
                    "suggestion": d.get("suggestion", ""),
                    "retryable": d.get("retryable", False),
                    "occurred_at": d.get("timestamp", ""),
                })
        except Exception:
            pass

        categories = FailureClassifier.categories()

        return {"failures": failures, "total": len(failures), "categories": categories}

    return router
