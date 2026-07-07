"""Test Failure Diagnosis Eval API (M113). Read-only endpoints."""
from fastapi import APIRouter

from bolt_core.test_failure_diagnosis_eval import FailureDiagnosisEvalService


def create_failure_diagnosis_eval_router() -> APIRouter:
    """创建测试失败诊断评估 API 路由。全部只读。"""
    service = FailureDiagnosisEvalService()

    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/failure-diagnosis/run")
    def run_failure_diagnosis_eval() -> dict:
        """运行全部测试失败诊断评估案例。只读，不修复任何问题。"""
        summary = service.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部失败诊断评估通过" if d["all_passed"] else "❌ 存在未通过的评估案例",
            "disclaimer": "评估验证失败分类和脱敏，不自动修复任何问题（is_auto_fix_allowed=false）。",
        }

    return router
