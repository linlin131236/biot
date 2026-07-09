"""Tool verification API router."""
from __future__ import annotations

from fastapi import APIRouter

from bolt_core.tool_verification_service import ToolVerificationService


def create_tool_verification_router(service: ToolVerificationService | None = None) -> APIRouter:
    router = APIRouter(tags=["tool-verification"])
    verifier = service or ToolVerificationService()

    @router.get("/tools/verify")
    def verify_tools() -> dict:
        """只读验证工具链健康状态。"""
        return verifier.verify_all()

    return router
