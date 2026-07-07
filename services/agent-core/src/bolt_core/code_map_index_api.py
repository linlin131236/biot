"""Code Map Index API router. Read-only code map for agent context."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.code_map_index import CodeMapIndexService


def create_code_map_index_router() -> APIRouter:
    router = APIRouter(tags=["code-map"])
    service = CodeMapIndexService(".")
    service.build_index()

    @router.get("/code-map/entries")
    def list_entries(category: str | None = Query(default=None)) -> list[dict]:
        """List all indexed code files, optionally filtered by category."""
        return service.list_entries(category=category)

    @router.get("/code-map/query")
    def query_entries(keyword: str = Query(...)) -> list[dict]:
        """Query code map by keyword."""
        if not keyword.strip():
            raise HTTPException(status_code=400, detail="keyword 不能为空。")
        return service.query(keyword)

    @router.get("/code-map/file")
    def file_summary(path: str = Query(...)) -> dict:
        """Get a single file's code map summary."""
        result = service.get_file_summary(path)
        if result is None:
            raise HTTPException(status_code=404, detail=f"未找到文件：{path}")
        return result

    @router.get("/code-map/summary")
    def index_summary() -> dict:
        """Get index summary statistics."""
        return service.summary()

    @router.get("/code-map/disclaimer")
    def disclaimer() -> dict:
        """Return the code map disclaimer."""
        return {
            "disclaimer": "代码地图是只读上下文索引，不授予执行权限。索引内容来自静态文件解析，不执行任何代码。",
            "excluded": [
                "node_modules", "dist", "build", "缓存目录",
                "虚拟环境 (.venv/venv)", "证书材料", "secret 文件",
                ".bolt", "uv.lock",
            ],
        }

    return router
