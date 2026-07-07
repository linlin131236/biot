"""Memory Permission Boundary API router."""
from fastapi import APIRouter, Query

from bolt_core.memory_permission_boundary import MemoryPermissionBoundary


def create_memory_permission_boundary_router() -> APIRouter:
    router = APIRouter(tags=["memory-permission-boundary"])
    boundary = MemoryPermissionBoundary()

    @router.post("/memory-permission/classify")
    def classify_content(payload: dict) -> dict:
        """分类记忆内容权限等级。只读诊断，不自动批准。

        请求体：{"content": "...", "source": "..."}
        返回：权限等级、可读/可写/可展示、中文解释、脱敏内容。
        """
        content = str(payload.get("content", ""))
        source = str(payload.get("source", ""))
        decision = boundary.classify(content, source)
        return decision.to_dict()

    @router.get("/memory-permission/tiers")
    def list_tiers() -> dict:
        """列出所有权限等级及其规则。只读。

        示例：GET /memory-permission/tiers
        """
        from bolt_core.memory_permission_boundary import (
            PermissionTier, _TIER_LABELS, _TIER_READABLE,
            _TIER_WRITABLE, _TIER_DISPLAYABLE,
        )
        tiers = []
        for tier in PermissionTier:
            tiers.append({
                "tier": tier.value,
                "label": _TIER_LABELS[tier],
                "can_read": _TIER_READABLE[tier],
                "can_write": _TIER_WRITABLE[tier],
                "can_display": _TIER_DISPLAYABLE[tier],
            })
        return {
            "tiers": tiers,
            "note": "unknown 类型默认保守阻断。secret 类型禁止保存和展示。",
        }

    @router.post("/memory-permission/check-write")
    def check_memory_write(payload: dict) -> dict:
        """检查内容是否可以写入长期记忆。

        请求体：{"content": "...", "source": "..."}
        返回：是否阻断、中文原因。
        """
        content = str(payload.get("content", ""))
        source = str(payload.get("source", ""))
        blocked, reason = boundary.should_block_memory_write(content, source)
        return {
            "can_write": not blocked,
            "blocked": blocked,
            "reason_cn": reason if blocked else "内容通过权限检查，可以写入（需用户确认）。",
        }

    return router
