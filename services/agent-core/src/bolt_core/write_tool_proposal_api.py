"""Write Tool Proposal API. Create, query, cancel proposals. Never writes to files."""
from fastapi import APIRouter, HTTPException

from bolt_core.write_tool_proposal import STATUS_PENDING, STATUS_APPROVED, WriteProposalStore


def create_write_tool_proposal_router(store: WriteProposalStore | None = None) -> APIRouter:
    """创建写入提案 API 路由。"""
    if store is None:
        store = WriteProposalStore()

    router = APIRouter(tags=["tools"])

    @router.post("/tools/proposal/create")
    def create_proposal(payload: dict) -> dict:
        """创建写入提案。不直接写文件。提案可被查询、取消、过期。"""
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="请求体必须是一个 JSON 对象")

        validation = store.create(**payload)
        if not validation.valid:
            raise HTTPException(status_code=400, detail={
                "message": "提案验证失败",
                "errors": validation.errors,
            })

        return {
            "proposal": validation.proposal.to_dict(),
            "disclaimer": "写入提案仅为结构化变更建议，不会直接修改任何文件。需要用户批准后才可 apply。",
        }

    @router.get("/tools/proposal/list")
    def list_proposals(status: str | None = None) -> dict:
        """列出所有提案。可选按状态过滤。只读。"""
        if status and status not in (STATUS_PENDING, STATUS_APPROVED, "applied", "cancelled", "expired", "stale"):
            raise HTTPException(status_code=400, detail=f"未知状态: {status}")
        proposals = store.list(status)
        return {
            "proposals": [p.to_dict() for p in proposals],
            "total": len(proposals),
            "disclaimer": "此 API 仅查询提案，不执行任何写入操作。",
        }

    @router.get("/tools/proposal/{proposal_id}")
    def get_proposal(proposal_id: str) -> dict:
        """查询单个提案详情。只读。"""
        proposal = store.get(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail=f"提案 '{proposal_id}' 不存在")
        return {
            "proposal": proposal.to_dict(),
            "disclaimer": "此 API 仅查询提案，不执行任何写入操作。",
        }

    @router.post("/tools/proposal/{proposal_id}/cancel")
    def cancel_proposal(proposal_id: str) -> dict:
        """取消一个待批准或已批准的提案。"""
        ok = store.cancel(proposal_id)
        if not ok:
            raise HTTPException(status_code=400, detail=f"无法取消提案 '{proposal_id}'（不存在或状态不允许取消）")
        proposal = store.get(proposal_id)
        return {
            "proposal": proposal.to_dict() if proposal else None,
            "message": "提案已取消",
        }

    @router.get("/tools/proposal/{proposal_id}/stale-check")
    def check_stale(proposal_id: str) -> dict:
        """检查提案是否因 git HEAD 变化而过期。只读。"""
        result = store.check_stale(proposal_id)
        if result.get("reason") and "不存在" in result.get("reason", ""):
            raise HTTPException(status_code=404, detail=result["reason"])
        return result

    return router
