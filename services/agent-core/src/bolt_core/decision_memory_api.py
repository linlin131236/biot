"""Decision Memory API router. Read-only access to project decisions."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.decision_memory import DecisionMemoryService


def create_decision_memory_router() -> APIRouter:
    router = APIRouter(tags=["decision-memory"])
    service = DecisionMemoryService(".")

    # ── Static routes (must be before dynamic /{decision_id}) ──────────

    @router.get("/decisions/summary")
    def decisions_summary() -> dict:
        """返回决策记忆概览：总数、里程碑分布。只读。

        示例：GET /decisions/summary
        """
        records = service.list_all()
        milestones: dict[str, int] = {}
        for r in records:
            m = r.milestone
            milestones[m] = milestones.get(m, 0) + 1

        return {
            "total_decisions": len(records),
            "milestone_distribution": milestones,
            "note": "此索引为只读快照，不自动写入新决策。决策来源：docs/decisions/*.md",
        }

    @router.get("/decisions/query/by-keyword")
    def query_decisions_by_keyword(keyword: str = Query(..., min_length=1)) -> list[dict]:
        """按关键词搜索决策。只读。

        示例：GET /decisions/query/by-keyword?keyword=安全
        """
        records = service.query_by_keyword(keyword)
        return [
            {
                "decision_id": r.decision_id,
                "milestone": r.milestone,
                "title": r.title,
                "summary_cn": r.summary_cn,
                "source_refs": r.source_refs,
            }
            for r in records
        ]

    # ── Dynamic routes ─────────────────────────────────────────────────

    @router.get("/decisions")
    def list_decisions(milestone: str | None = Query(default=None)) -> list[dict]:
        """列出所有决策，可按 milestone 筛选。只读，不写入新决策。

        示例：GET /decisions?milestone=M70
        """
        if milestone:
            records = service.query_by_milestone(milestone)
        else:
            records = service.list_all()

        return [
            {
                "decision_id": r.decision_id,
                "milestone": r.milestone,
                "title": r.title,
                "summary_cn": r.summary_cn,
                "source_refs": r.source_refs,
            }
            for r in records
        ]

    @router.get("/decisions/{decision_id}")
    def get_decision(decision_id: str) -> dict:
        """获取单条决策完整详情。只读。

        示例：GET /decisions/072-code-map-index
        """
        record = service.get_detail(decision_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到决策：{decision_id}。请确认 decision_id 正确，或先调用 GET /decisions 查看可用列表。",
            )
        return record.to_dict()

    return router
