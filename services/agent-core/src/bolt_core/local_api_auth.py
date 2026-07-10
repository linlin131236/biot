import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


PUBLIC_PATHS = {"/health"}


def install_local_api_auth(app: FastAPI, token: str | None, *, require_token: bool = True) -> None:
    if not token:
        if not require_token:
            return
        raise RuntimeError(
            "本地 API 鉴权令牌未配置，拒绝以裸奔模式启动。"
            "请通过 local_api_token 参数或 BOLT_AGENT_CORE_TOKEN 环境变量提供。"
        )

    expected = f"Bearer {token}"

    @app.middleware("http")
    async def require_local_api_token(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not secrets.compare_digest(authorization, expected):
            return JSONResponse(status_code=401, content={"detail": "缺少或无效的本地访问令牌"})
        return await call_next(request)
