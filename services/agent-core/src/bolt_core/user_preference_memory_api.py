"""User Preference Memory API router. Read-only, strictly controlled."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.user_preference_memory import UserPreferenceMemoryService


def create_user_preference_memory_router() -> APIRouter:
    router = APIRouter(tags=["user-preference-memory"])
    service = UserPreferenceMemoryService(".")

    @router.get("/preferences/summary")
    def preferences_summary() -> dict:
        """返回偏好概览：总数、分类分布。只读。

        示例：GET /preferences/summary
        """
        records = service.list_all()
        categories: dict[str, int] = {}
        for r in records:
            cat = r.category
            categories[cat] = categories.get(cat, 0) + 1

        auto_count = sum(1 for r in records if r.can_apply_automatically)
        confirm_count = sum(1 for r in records if r.requires_confirmation)

        return {
            "total_preferences": len(records),
            "category_distribution": categories,
            "auto_apply_count": auto_count,
            "requires_confirmation_count": confirm_count,
            "note": "此索引为只读。偏好来源：project-state 硬规则 + 用户明确指令。不从一次性上下文推断。不存储 secret。",
        }

    @router.get("/preferences")
    def list_preferences(category: str | None = Query(default=None)) -> list[dict]:
        """列出所有偏好，可按分类筛选。只读。

        示例：GET /preferences?category=safety
        """
        if category:
            records = service.query_by_category(category)
        else:
            records = service.list_all()
        return [r.to_dict() for r in records]

    @router.get("/preferences/{preference_id}")
    def get_preference(preference_id: str) -> dict:
        """获取单条偏好详情。只读。

        示例：GET /preferences/pref-001-language
        """
        record = service.get_detail(preference_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到偏好：{preference_id}。请先调用 GET /preferences 查看可用列表。",
            )
        return record.to_dict()

    @router.get("/preferences/query/by-keyword")
    def query_preferences_by_keyword(keyword: str = Query(..., min_length=1)) -> list[dict]:
        """按关键词搜索偏好。只读。

        示例：GET /preferences/query/by-keyword?keyword=安全
        """
        records = service.query_by_keyword(keyword)
        return [r.to_dict() for r in records]

    @router.get("/preferences/check/conflicts")
    def check_preference_conflicts() -> dict:
        """检查偏好冲突，返回中文冲突说明。只读。

        示例：GET /preferences/check/conflicts
        """
        conflicts = service.check_conflicts()
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "note": "偏好冲突检查为只读诊断，不自动修改任何偏好。",
        }

    @router.get("/preferences/check/secret")
    def check_secret_attempt(text: str = Query(..., min_length=1)) -> dict:
        """检查给定文本是否包含 secret 模式（token/key/cert）。只读。

        示例：GET /preferences/check/secret?text=sk-abc123...
        """
        is_secret = service.is_secret_attempt(text)
        return {
            "contains_secret_pattern": is_secret,
            "note": "此检查用于防止 secret 进入长期记忆。仅供诊断参考，不存储输入文本。" if is_secret
                   else "未检测到 secret 模式。",
        }

    return router
