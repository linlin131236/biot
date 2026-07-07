"""Approval Apply API. Apply approved proposals after human verification."""
from fastapi import APIRouter, HTTPException

from bolt_core.approval_apply import ApprovalApplyEngine
from bolt_core.write_tool_proposal import WriteProposalStore


def create_approval_apply_router(store: WriteProposalStore | None = None) -> APIRouter:
    """创建批准应用 API 路由。"""
    if store is None:
        store = WriteProposalStore()
    engine = ApprovalApplyEngine(store=store)

    router = APIRouter(tags=["tools"])

    @router.post("/tools/approval/apply")
    def apply_proposal(payload: dict) -> dict:
        """应用已批准的提案。必须通过所有安全检查。

        请求体: { "proposal_id": "...", "approval": { "actor": "human", "scope": "..." } }
        """
        proposal_id = str(payload.get("proposal_id", "")).strip()
        if not proposal_id:
            raise HTTPException(status_code=400, detail="proposal_id 不能为空")

        approval = payload.get("approval", {})
        if not isinstance(approval, dict):
            raise HTTPException(status_code=400, detail="approval 必须是一个对象")

        result = engine.apply(proposal_id, approval)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.reason)

        return {
            "result": result.to_dict(),
            "disclaimer": "补丁已应用，审计记录已保存。delete/push/release/tag 操作未在本 milestone 范围内执行。",
        }

    @router.get("/tools/approval/audit-log")
    def get_audit_log() -> dict:
        """查看 apply 审计日志。只读。"""
        return {
            "audit_log": engine.audit_log(),
            "total": len(engine.audit_log()),
        }

    return router
