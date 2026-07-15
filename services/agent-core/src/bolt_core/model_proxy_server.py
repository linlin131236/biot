"""Loopback-only HTTP surface for the Core-owned runtime model proxy."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock, Thread
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from bolt_core.model_proxy import RuntimeModelProxy

_MAX_BODY_BYTES = 64 * 1024


class ModelProxyServer:
    def __init__(self, proxy: "RuntimeModelProxy") -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(proxy))
        self._thread: Thread | None = None
        self._lock = Lock()
        self._stopped = False

    @property
    def host(self) -> str:
        return "127.0.0.1"

    @property
    def port(self) -> int:
        return self._server.server_port

    def start(self) -> None:
        with self._lock:
            if self._stopped:
                raise RuntimeError("model proxy server cannot restart after shutdown")
            if self._thread is not None:
                return
            self._thread = Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            thread = self._thread
        if thread is None:
            self._server.server_close()
            return
        self._server.shutdown()
        self._server.server_close()
        thread.join(timeout=1)


class _ProxyHandler(BaseHTTPRequestHandler):
    _proxy: "RuntimeModelProxy"

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions" or self.headers.get("Authorization"):
            self._send(HTTPStatus.FORBIDDEN, {"error": "request_not_allowed"})
            return
        token = self.headers.get("X-Bolt-Runtime-Token")
        payload = self._read_payload()
        if token is None or payload is None:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
            return
        self._complete(token, payload)

    def log_message(self, _format: str, *_args) -> None:
        return

    def _complete(self, token: str, payload: dict) -> None:
        try:
            response = self._proxy.complete(_request_from_payload(token, self.path, payload))
        except Exception as error:
            self._send(HTTPStatus.FORBIDDEN, {"error": _error_code(error)})
            return
        self._send(HTTPStatus.OK, response)

    def _read_payload(self) -> dict | None:
        length = self.headers.get("Content-Length")
        if not length or not length.isdigit() or int(length) > _MAX_BODY_BYTES:
            return None
        try:
            value = json.loads(self.rfile.read(int(length)))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _send(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _handler(proxy: "RuntimeModelProxy") -> type[_ProxyHandler]:
    class Handler(_ProxyHandler):
        _proxy = proxy

    return Handler


def _request_from_payload(token: str, path: str, payload: dict):
    from bolt_core.model_proxy import ModelProxyRequest

    return ModelProxyRequest(token, f"request_{uuid4().hex}", path, payload)


def _error_code(error: Exception) -> str:
    text = str(error)
    if "budget" in text:
        return "budget_exceeded"
    if "expired" in text:
        return "timeout"
    if "path" in text:
        return "provider_error"
    return "auth"
