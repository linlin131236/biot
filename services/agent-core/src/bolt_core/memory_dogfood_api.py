"""Memory Dogfood API router. Readiness assessment for V3 memory layer."""
from fastapi import APIRouter

from bolt_core.memory_dogfood import MemoryDogfoodService


def create_memory_dogfood_router() -> APIRouter:
    router = APIRouter(tags=["memory-dogfood"])
    service = MemoryDogfoodService(".")

    @router.get("/dogfood/memory")
    def memory_dogfood() -> dict:
        """M80 Memory Dogfood：V3 记忆层全量就绪度评估。

        检查 M71-M79 所有组件：功能、source_refs、安全性、无自动执行、未进入 M81。
        全部通过才建议进入 M81。
        """
        result = service.assess()
        return result.to_dict()

    return router
