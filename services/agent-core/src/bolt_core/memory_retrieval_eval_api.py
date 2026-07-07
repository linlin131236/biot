"""Memory Retrieval Eval API (M116). Read-only."""
from fastapi import APIRouter
from bolt_core.memory_retrieval_eval import MemoryRetrievalEvalService


def create_memory_retrieval_eval_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/memory-retrieval/run")
    def run_memory_eval() -> dict:
        summary = MemoryRetrievalEvalService.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部记忆检索评估通过" if d["all_passed"] else "❌ 存在未通过",
            "disclaimer": "记忆检索评估使用fixture数据，不访问真实记忆存储。",
        }

    return router
