"""Researcher Integration API router. Read-only research briefs and summaries."""
from fastapi import APIRouter, HTTPException

from bolt_core.researcher_integration import ResearcherIntegrationService


def create_researcher_integration_router() -> APIRouter:
    router = APIRouter(tags=["researcher-integration"])
    service = ResearcherIntegrationService()

    @router.get("/research/scopes")
    def list_scopes() -> list[dict]:
        """列出所有有效的研究范围。只读。"""
        return service.scope_options()

    @router.post("/research/briefs")
    def create_brief(payload: dict) -> dict:
        """创建研究摘要。只读角色，不修改文件。

        payload: { title_cn, question_cn, allowed_sources, scope }
        allowed_sources 限 2-4 篇。
        """
        result = service.create_brief(
            title_cn=payload.get("title_cn", ""),
            question_cn=payload.get("question_cn", ""),
            allowed_sources=payload.get("allowed_sources", []),
            scope=payload.get("scope", ""),
        )
        if isinstance(result, dict):
            # Already a dict from ResearchValidation
            return result
        # It's a ResearchBrief
        if hasattr(result, 'blocked') and result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        if not hasattr(result, 'valid'):
            # It's a ResearchBrief (success)
            return result.to_dict()
        # ResearchValidation
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.get("/research/briefs")
    def list_briefs() -> list[dict]:
        """列出所有研究摘要。只读。"""
        return [b.to_dict() for b in service.list_briefs()]

    @router.get("/research/briefs/{brief_id}")
    def get_brief(brief_id: str) -> dict:
        """获取研究摘要详情。只读。"""
        brief = service.get_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail=f"未找到研究摘要：{brief_id}。")
        return brief.to_dict()

    @router.post("/research/execute")
    def execute_brief(payload: dict) -> dict:
        """执行研究摘要，查询数据源并产生结构化摘要。只读，不修改文件。

        payload: { brief_id }
        """
        brief_id = str(payload.get("brief_id", "")).strip()
        if not brief_id:
            raise HTTPException(status_code=400, detail="brief_id 不能为空")
        result = service.execute_brief(brief_id)
        if hasattr(result, 'blocked') and result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        if hasattr(result, 'valid') and not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.post("/research/summaries")
    def produce_summary(payload: dict) -> dict:
        """提交研究摘要输出。必须有 source_refs。

        payload: { brief_id, summary_cn, principles_cn, risks_cn, source_refs }
        """
        result = service.produce_summary(
            brief_id=payload.get("brief_id", ""),
            summary_cn=payload.get("summary_cn", ""),
            principles_cn=payload.get("principles_cn", []),
            risks_cn=payload.get("risks_cn", []),
            source_refs=payload.get("source_refs", []),
        )
        if hasattr(result, 'blocked') and result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        if not hasattr(result, 'valid'):
            return result.to_dict()
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.get("/research/summaries")
    def list_summaries() -> list[dict]:
        """列出所有研究摘要输出。只读。"""
        return [s.to_dict() for s in service.list_summaries()]

    @router.get("/research/summaries/{brief_id}")
    def get_summary(brief_id: str) -> dict:
        """获取研究摘要输出详情。只读。"""
        summary = service.get_summary(brief_id)
        if summary is None:
            raise HTTPException(status_code=404, detail=f"未找到研究输出：{brief_id}。")
        return summary.to_dict()

    @router.post("/research/validate-source-refs")
    def validate_source_refs(payload: dict) -> dict:
        """验证 source_refs 是否合规。只读诊断。"""
        result = service.validate_source_refs(payload.get("source_refs", []))
        return result.to_dict()

    return router
