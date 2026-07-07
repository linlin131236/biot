"""Chinese Interaction Quality Eval API (M117). Read-only."""
from fastapi import APIRouter
from bolt_core.chinese_interaction_eval import ChineseInteractionEvalService


def create_chinese_interaction_eval_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/chinese-interaction/run")
    def run_chinese_eval() -> dict:
        summary = ChineseInteractionEvalService.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部中文交互评估通过" if d["all_passed"] else "❌ 存在未通过",
            "disclaimer": "中文交互评估仅检查文本质量，不修改任何内容。",
        }

    return router
