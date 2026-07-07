"""Reviewer Independent Gate API router."""
from fastapi import APIRouter, HTTPException

from bolt_core.reviewer_independent_gate import ReviewerIndependentGateService


def create_reviewer_independent_gate_router() -> APIRouter:
    router = APIRouter(tags=["reviewer-independent-gate"])
    service = ReviewerIndependentGateService()

    @router.post("/review-gate/evaluate")
    def evaluate(payload: dict) -> dict:
        """评估审查包。独立审查门。

        硬阻断：
        - 构建者与审查者同上下文（自我批准）
        - 缺 evidence/source_refs

        示例：POST /review-gate/evaluate
        Body: { workflow_id, builder_context, reviewer_context, ... }
        """
        result = service.evaluate(
            workflow_id=payload.get("workflow_id", ""),
            builder_context=payload.get("builder_context", ""),
            reviewer_context=payload.get("reviewer_context", ""),
            builder_output_summary=payload.get("builder_output_summary", ""),
            code_changes=payload.get("code_changes", ""),
            tests_status=payload.get("tests_status", ""),
            evidence_refs=payload.get("evidence_refs", []),
            source_refs=payload.get("source_refs", []),
            findings=payload.get("findings"),
            residual_risks=payload.get("residual_risks"),
        )
        if result.verdict == "blocked":
            raise HTTPException(status_code=400, detail=result.summary_cn)
        return result.to_dict()

    @router.get("/review-gate/results")
    def list_results() -> list[dict]:
        """列出所有审查门结果。只读。"""
        return [r.to_dict() for r in service.list_results()]

    @router.get("/review-gate/results/{review_id}")
    def get_result(review_id: str) -> dict:
        """获取审查门结果详情。只读。"""
        r = service.get_result(review_id)
        if r is None:
            raise HTTPException(status_code=404, detail=f"未找到审查结果：{review_id}。")
        return r.to_dict()

    return router
