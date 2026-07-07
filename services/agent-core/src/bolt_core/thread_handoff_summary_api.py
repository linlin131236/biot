"""Thread Handoff Summary API router. New-window handoff documents."""
from fastapi import APIRouter, Query

from bolt_core.thread_handoff_summary import ThreadHandoffSummaryService


def create_thread_handoff_summary_router() -> APIRouter:
    router = APIRouter(tags=["thread-handoff-summary"])
    service = ThreadHandoffSummaryService(".")

    @router.get("/handoff/summary")
    def get_handoff_summary(format: str = Query(default="json")) -> dict | str:
        """生成新窗口接手摘要。适合直接复制给新 AI 窗口。

        参数：
        - format：输出格式（json 或 markdown）

        不包含 secret。不把整个历史粘贴出来。
        明确声明：不自动执行、不自动 push、不进入未授权 milestone。
        """
        summary = service.generate()

        if format == "markdown":
            from fastapi.responses import PlainTextResponse
            md = summary.to_markdown()
            return PlainTextResponse(content=md, media_type="text/plain; charset=utf-8")

        return summary.to_dict()

    return router
