"""Patch Apply Eval API (M112). Read-only endpoints for patch apply evaluation."""
import tempfile
from pathlib import Path

from fastapi import APIRouter

from bolt_core.patch_apply_eval import PatchApplyEvalService


def create_patch_apply_eval_router() -> APIRouter:
    """创建补丁应用评估 API 路由。全部只读，在临时目录运行。"""
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/patch-apply/run")
    def run_patch_apply_eval() -> dict:
        """运行全部补丁应用评估案例。在临时目录执行，不修改真实文件。"""
        with tempfile.TemporaryDirectory(prefix="bolt_patch_eval_") as tmp:
            summary = PatchApplyEvalService.run_all(Path(tmp))
            d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部补丁应用评估通过" if d["all_passed"] else "❌ 存在未通过的评估案例",
            "disclaimer": "评估在临时目录中运行，未修改任何真实项目文件。",
        }

    return router
