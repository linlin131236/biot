"""Reviewer API router. Reads Builder output and produces review findings.
Strict Gate: P0/P1 block approval, P2 triggers changes_requested.
"""
from fastapi import APIRouter, HTTPException

from bolt_core.reviewer_engine import ReviewerEngine
from bolt_core.multi_agent_workflow_models import BuilderOutput


def create_reviewer_router() -> APIRouter:
    router = APIRouter(tags=["reviewer"])
    engine = ReviewerEngine()

    @router.post("/reviewer/review")
    def review_builder_output(payload: dict) -> dict:
        """审查 Builder 输出，返回结构化审查发现。严格 Gate：P0/P1 阻止批准，P2 触发需修改。

        payload: { code_changes, tests, evidence_refs, source_refs }
        """
        code_changes = str(payload.get("code_changes", ""))
        tests = str(payload.get("tests", ""))
        evidence_refs = payload.get("evidence_refs", [])
        source_refs = payload.get("source_refs", [])

        builder_output = BuilderOutput(
            code_changes=code_changes,
            tests=tests,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
        )
        result = engine.review_output(builder_output, code_changes)
        return result.to_dict()

    @router.get("/reviewer/verdict/{verdict}")
    def get_verdict_label(verdict: str) -> dict:
        """获取 verdict 中文标签。"""
        labels = {
            "approved": "已批准",
            "changes_requested": "需修改",
            "blocked": "已阻塞",
        }
        label = labels.get(verdict, verdict)
        return {"verdict": verdict, "label_cn": label}

    return router
