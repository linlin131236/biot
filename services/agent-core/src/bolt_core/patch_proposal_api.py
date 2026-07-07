"""Patch Proposal API. Create, preview, list patches. Never applies to files."""
from fastapi import APIRouter, HTTPException

from bolt_core.patch_proposal import PatchProposalEngine


def create_patch_proposal_router(engine: PatchProposalEngine | None = None) -> APIRouter:
    """创建补丁提案 API 路由。"""
    if engine is None:
        engine = PatchProposalEngine()

    router = APIRouter(tags=["tools"])

    @router.post("/tools/patch/create")
    def create_patch(payload: dict) -> dict:
        """创建补丁提案。验证通过后生成不可变补丁。不应用到文件。"""
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="请求体必须是一个 JSON 对象")

        validation = engine.create(**payload)
        if not validation.valid:
            raise HTTPException(status_code=400, detail={
                "message": "补丁验证失败",
                "errors": validation.errors,
                "warnings": validation.warnings,
            })

        return {
            "validation": validation.to_dict(),
            "disclaimer": "补丁提案仅用于预览和审计，未应用到任何真实文件。",
        }

    @router.get("/tools/patch/list")
    def list_patches() -> dict:
        """列出所有补丁提案。只读。"""
        patches = engine.list()
        return {
            "patches": [p.to_dict() for p in patches],
            "total": len(patches),
        }

    @router.get("/tools/patch/{patch_id}")
    def get_patch(patch_id: str) -> dict:
        """查询单个补丁。只读。"""
        patch = engine.get(patch_id)
        if patch is None:
            raise HTTPException(status_code=404, detail=f"补丁 '{patch_id}' 不存在")
        return {"patch": patch.to_dict()}

    @router.get("/tools/patch/{patch_id}/preview")
    def preview_patch(patch_id: str) -> dict:
        """预览补丁内容。不应用。"""
        preview = engine.preview(patch_id)
        if "error" in preview:
            raise HTTPException(status_code=404, detail=preview["error"])
        return preview

    return router
