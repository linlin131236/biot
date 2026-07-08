"""SkillLearner Review Loop API."""
from fastapi import APIRouter, HTTPException
from bolt_core.skilllearner_review_loop import SkillLearnerReviewLoopService


def create_skilllearner_review_loop_router() -> APIRouter:
    router = APIRouter(tags=["skilllearner-review-loop"])
    service = SkillLearnerReviewLoopService()

    @router.post("/skill-learner/failures")
    def record_failure(payload: dict) -> dict:
        return service.record_failure(
            failure_class=payload.get("failure_class", ""),
            failure_id=payload.get("failure_id", ""),
            description_cn=payload.get("description_cn", ""),
        )

    @router.get("/skill-learner/analyze")
    def analyze() -> dict:
        return service.analyze()

    @router.post("/skill-learner/proposals")
    def propose(payload: dict) -> dict:
        result = service.propose_improvement(
            title_cn=payload.get("title_cn", ""),
            failure_class=payload.get("failure_class", ""),
            options=payload.get("options"),
            target_type=payload.get("target_type", "unknown"),
            evidence_refs=payload.get("evidence_refs"),
            source_refs=payload.get("source_refs"),
        )
        return result.to_dict()

    @router.get("/skill-learner/proposals")
    def list_proposals() -> list[dict]:
        return [p.to_dict() for p in service.list_proposals()]

    @router.get("/skill-learner/proposals/{proposal_id}")
    def get_proposal(proposal_id: str) -> dict:
        p = service.get_proposal(proposal_id)
        if p is None:
            raise HTTPException(404, f"未找到提案：{proposal_id}")
        return p.to_dict()

    @router.post("/skill-learner/auto-scan")
    def auto_scan(payload: dict) -> dict:
        """主动扫描失败记忆，自动检测模式并生成改进提案。

        payload: { keyword?, category? }
        """
        keyword = str(payload.get("keyword", ""))
        # Note: failure_memory query interface would be injected in production
        # For now, auto_scan with no failure_memory returns a guide response
        result = service.auto_scan(failure_memory=None, keyword=keyword)
        return result

    return router
