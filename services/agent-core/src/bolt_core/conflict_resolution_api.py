"""Conflict Resolution API."""
from fastapi import APIRouter, HTTPException
from bolt_core.conflict_resolution import ConflictResolutionService


def create_conflict_resolution_router() -> APIRouter:
    router = APIRouter(tags=["conflict-resolution"])
    service = ConflictResolutionService()

    @router.post("/conflicts/detect")
    def detect(payload: dict) -> dict:
        result = service.detect(
            conflict_type=payload.get("conflict_type", "unknown"),
            description_cn=payload.get("description_cn", ""),
            party_a=payload.get("party_a", ""),
            party_b=payload.get("party_b", ""),
            source_refs=payload.get("source_refs"),
        )
        return result.to_dict()

    @router.get("/conflicts")
    def list_conflicts(resolved: bool | None = None) -> list[dict]:
        return [c.to_dict() for c in service.list_conflicts(resolved)]

    @router.get("/conflicts/{conflict_id}")
    def get_conflict(conflict_id: str) -> dict:
        c = service.get_conflict(conflict_id)
        if c is None:
            raise HTTPException(404, f"未找到冲突：{conflict_id}")
        return c.to_dict()

    @router.post("/conflicts/{conflict_id}/resolve")
    def resolve(conflict_id: str, payload: dict) -> dict:
        c = service.resolve(conflict_id, payload.get("option", ""), payload.get("resolution_cn", ""))
        if c is None:
            raise HTTPException(404, f"未找到冲突：{conflict_id}")
        return c.to_dict()

    return router
