"""Context Compaction API router. Compact project context summary."""
from fastapi import APIRouter, Query

from bolt_core.context_compaction import ContextCompactionService


def create_context_compaction_router() -> APIRouter:
    router = APIRouter(tags=["context-compaction"])
    service = ContextCompactionService(".")

    @router.get("/context/compact")
    def compact_context(
        max_items: int = Query(default=50, ge=5, le=200),
        format: str = Query(default="json"),
    ) -> dict | str:
        """生成中文结构化上下文压缩摘要。

        参数：
        - max_items：每节最大条目数（5-200，默认50）
        - format：输出格式（json 或 markdown）

        安全硬规则永不截断。
        不调用 LLM，纯数据组合。
        """
        summary = service.compact(max_items=max_items)

        if format == "markdown":
            from fastapi.responses import PlainTextResponse
            md = summary.to_markdown()
            token_est = service.estimate_tokens(summary)
            md += f"\n\n---\n*预估 token 数：~{token_est}*"
            return PlainTextResponse(content=md, media_type="text/plain; charset=utf-8")

        result = summary.to_dict()
        result["estimated_tokens"] = service.estimate_tokens(summary)
        return result

    @router.get("/context/compact/tokens")
    def estimate_tokens(max_items: int = Query(default=50, ge=5, le=200)) -> dict:
        """预估压缩摘要的 token 消耗。只读。

        示例：GET /context/compact/tokens?max_items=30
        """
        summary = service.compact(max_items=max_items)
        return {
            "estimated_tokens": service.estimate_tokens(summary),
            "max_items": max_items,
            "note": "此为粗略估算（中文 ~0.7 token/字，英文 ~0.25 token/字）。实际 token 数以模型 tokenizer 为准。",
        }

    return router
