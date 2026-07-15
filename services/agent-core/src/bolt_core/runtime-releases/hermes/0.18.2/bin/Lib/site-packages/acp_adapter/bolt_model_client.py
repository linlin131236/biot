"""Core-owned model client injected into Bolt's managed Hermes ACP payload.

This file is copied into the pinned Hermes staging tree as
``acp_adapter/bolt_model_client.py``.  It deliberately exposes only the small
OpenAI-compatible surface that Hermes' main conversation loop consumes.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
import json
from threading import RLock
from types import SimpleNamespace
from typing import Any


_REQUEST_TIMEOUT_SECONDS = 125


class _ChatCompletions:
    def __init__(self, client: "BoltModelClient") -> None:
        self._client = client

    def create(self, **kwargs: Any) -> Any:
        return self._client._complete(kwargs)


class BoltModelClient:
    """Use the parent ACP connection instead of a network Provider endpoint."""

    def __init__(self, session_id: str) -> None:
        self.chat = SimpleNamespace(completions=_ChatCompletions(self))
        self._session_id = session_id
        self._connection = None
        self._loop = None
        self._pending: Future[Any] | None = None
        self._closed = False
        self._lock = RLock()

    def bind(self, connection: Any, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Bolt ACP model client is closed")
            self._connection = connection
            self._loop = loop

    def unbind(self) -> None:
        with self._lock:
            pending, self._pending = self._pending, None
            self._connection = None
            self._loop = None
        if pending is not None:
            pending.cancel()

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.unbind()

    def _complete(self, request: dict[str, Any]) -> Any:
        if request.get("stream"):
            raise RuntimeError("Bolt ACP model client does not support streaming")
        payload = dict(request)
        payload.pop("model", None)
        payload.pop("stream", None)
        _json_value(payload)
        with self._lock:
            if self._closed or self._connection is None or self._loop is None:
                raise RuntimeError("Bolt ACP model authority is unavailable")
            future = asyncio.run_coroutine_threadsafe(
                self._connection.ext_method(
                    "bolt/model.complete",
                    {"sessionId": self._session_id, "payload": payload},
                ),
                self._loop,
            )
            self._pending = future
        try:
            response = future.result(timeout=_REQUEST_TIMEOUT_SECONDS)
        finally:
            with self._lock:
                if self._pending is future:
                    self._pending = None
        return _object(response)


def bind_bolt_model_client(agent: Any, connection: Any, loop: asyncio.AbstractEventLoop) -> None:
    client = getattr(agent, "client", None)
    if isinstance(client, BoltModelClient):
        client.bind(connection, loop)


def unbind_bolt_model_client(agent: Any) -> None:
    client = getattr(agent, "client", None)
    if isinstance(client, BoltModelClient):
        client.unbind()


def _json_value(value: Any) -> None:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("Bolt ACP model payload is invalid") from error


def _object(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{str(key): _object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_object(item) for item in value]
    return value
