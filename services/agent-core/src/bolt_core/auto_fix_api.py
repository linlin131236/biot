"""Self-review auto-fix API router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bolt_core.auto_fix_service import AutoFixService


def create_auto_fix_router(service: AutoFixService | None = None) -> APIRouter:
    router = APIRouter(tags=["auto-fix"])
    auto_fix_service = service or AutoFixService()

    @router.post("/reviewer/auto-fix")
    def auto_fix(payload: dict) -> dict:
        """生成低风险审查发现的自动修复提案，不直接写文件。"""
        findings = payload.get("findings", [])
        if not isinstance(findings, list):
            raise HTTPException(status_code=400, detail="findings 必须是数组")
        code_changes = str(payload.get("code_changes", ""))
        return auto_fix_service.auto_fix(findings, code_changes)

    return router
