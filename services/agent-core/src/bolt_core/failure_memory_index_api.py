"""Failure Memory Index API router. Read-only failure history."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.failure_memory_index import FailureMemoryIndexService


def create_failure_memory_index_router() -> APIRouter:
    router = APIRouter(tags=["failure-memory-index"])
    service = FailureMemoryIndexService(".")

    @router.get("/failures/summary")
    def failures_summary() -> dict:
        """返回失败记忆概览：总数、分类分布、严重度分布。只读。

        示例：GET /failures/summary
        """
        records = service.list_all()
        categories: dict[str, int] = {}
        severities: dict[str, int] = {}
        for r in records:
            cat_label = r.category
            categories[cat_label] = categories.get(cat_label, 0) + 1
            sev = r.severity
            severities[sev] = severities.get(sev, 0) + 1

        return {
            "total_failures": len(records),
            "category_distribution": categories,
            "severity_distribution": severities,
            "note": "此索引为只读快照，不自动修复、不自动重试、不自动批准。数据来源：review gates + project-state。",
        }

    @router.get("/failures")
    def list_failures(
        category: str | None = Query(default=None),
        severity: str | None = Query(default=None),
    ) -> list[dict]:
        """列出所有失败记录，可按分类/严重度筛选。只读。

        示例：GET /failures?category=test_failure&severity=P1
        """
        if category:
            records = service.query_by_category(category)
        else:
            records = service.list_all()

        if severity:
            sev_upper = severity.upper()
            records = [r for r in records if r.severity.upper() == sev_upper]

        return [
            {
                "failure_id": r.failure_id,
                "category": r.category,
                "severity": r.severity,
                "milestone": r.milestone,
                "symptom_cn": r.symptom_cn,
                "source_refs": r.source_refs,
            }
            for r in records
        ]

    @router.get("/failures/{failure_id}")
    def get_failure(failure_id: str) -> dict:
        """获取单条失败详情。只读。

        示例：GET /failures/phase-57-p1
        """
        record = service.get_detail(failure_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到失败记录：{failure_id}。请先调用 GET /failures 查看可用列表。",
            )
        return record.to_dict()

    @router.get("/failures/query/by-keyword")
    def query_failures_by_keyword(keyword: str = Query(..., min_length=1)) -> list[dict]:
        """按关键词搜索失败记录。只读。

        示例：GET /failures/query/by-keyword?keyword=whitespace
        """
        records = service.query_by_keyword(keyword)
        return [
            {
                "failure_id": r.failure_id,
                "category": r.category,
                "severity": r.severity,
                "milestone": r.milestone,
                "symptom_cn": r.symptom_cn,
                "source_refs": r.source_refs,
            }
            for r in records
        ]

    return router
