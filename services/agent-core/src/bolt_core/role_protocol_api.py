"""Role Protocol API router. Read-only endpoints for role definitions,
validation, boundaries, and handoff format."""
from fastapi import APIRouter, HTTPException

from bolt_core.role_protocol import RoleProtocolService


def create_role_protocol_router() -> APIRouter:
    router = APIRouter(tags=["role-protocol"])
    service = RoleProtocolService()

    # ── Static routes MUST come before dynamic /roles/{role_id} ────────

    @router.get("/roles/handoff-format")
    def get_handoff_format() -> dict:
        """获取标准交接格式说明。只读。

        示例：GET /roles/handoff-format
        """
        return service.get_handoff_format()

    # ── Dynamic routes ─────────────────────────────────────────────────

    @router.get("/roles")
    def list_roles() -> list[dict]:
        """列出全部 5 个多 Agent 角色。只读。

        示例：GET /roles
        返回：planner, researcher, builder, reviewer, skill_learner
        """
        roles = service.list_roles()
        return [r.to_dict() for r in roles]

    @router.get("/roles/{role_id}")
    def get_role(role_id: str) -> dict:
        """获取单个角色详情（中文）。只读。

        示例：GET /roles/builder
        """
        role = service.get_role(role_id)
        if role is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到角色：{role_id}。可用角色：{', '.join(service.role_ids())}。",
            )
        return role.to_dict()

    @router.get("/roles/{role_id}/boundary")
    def explain_boundary(role_id: str) -> dict:
        """获取角色边界中文说明。只读。

        返回：角色能做什么、不能做什么、输出要求、可移交对象。

        示例：GET /roles/builder/boundary
        """
        result = service.explain_boundary(role_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.post("/roles/validate-output")
    def validate_role_output(payload: dict) -> dict:
        """验证角色输出是否满足要求。只读诊断。

        payload: { role_id: str, output_data: dict }
        检查：必要字段、evidence_refs/source_refs、角色特定要求。

        示例：POST /roles/validate-output
        Body: {"role_id":"builder", "output_data":{"evidence_refs":["test.log"]}}
        """
        role_id = payload.get("role_id", "")
        output_data = payload.get("output_data", {})
        if not role_id:
            raise HTTPException(status_code=400, detail="缺少 role_id 字段。")
        result = service.validate_output(role_id, output_data)
        if result.blocked and not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.post("/roles/validate-transition")
    def validate_transition(payload: dict) -> dict:
        """验证角色间转换是否合法。只读。

        payload: { from_role_id: str, to_role_id: str }
        检查：角色是否存在、是否在允许的移交列表中、是否存在自我批准风险。

        示例：POST /roles/validate-transition
        Body: {"from_role_id":"builder", "to_role_id":"reviewer"}
        """
        from_role = payload.get("from_role_id", "")
        to_role = payload.get("to_role_id", "")
        if not from_role or not to_role:
            raise HTTPException(
                status_code=400, detail="缺少 from_role_id 或 to_role_id 字段。"
            )
        result = service.validate_transition(from_role, to_role)
        if result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    return router
