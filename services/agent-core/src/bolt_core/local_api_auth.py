import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def install_local_api_auth(app: FastAPI, token: str | None) -> None:
    if not token:
        return

    expected = f"Bearer {token}"

    @app.middleware("http")
    async def require_local_api_token(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not secrets.compare_digest(authorization, expected):
            return JSONResponse(status_code=401, content={"detail": "缺少或无效的本地访问令牌"})
        return await call_next(request)
