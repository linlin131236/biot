"""Bounded JSON-RPC transport for a managed ACP stdio process."""
from __future__ import annotations

from contextlib import suppress
import json
from queue import Empty, Full, Queue
from threading import Event, Lock, RLock, Thread, local
from typing import Any, Callable


class AcpTransportError(ValueError):
    """The managed ACP process can no longer exchange JSON-RPC messages."""


_MAX_MESSAGE_BYTES = 1024 * 1024
_MAX_PARAMS_BYTES = 256 * 1024
_MAX_INBOUND_REQUESTS = 8
_RUNTIME_REQUEST_METHODS = frozenset({"_bolt/model.complete", "session/request_permission"})


class AcpStdioClient:
    def __init__(
        self,
        process,
        notification_handler: Callable[[dict[str, Any]], None],
        request_handler: Callable[["AcpStdioClient", dict[str, Any]], None],
        lifecycle_handler: Callable[[AcpTransportError], None] | None = None,
    ) -> None:
        self._process = process
        self._notification_handler = notification_handler
        self._request_handler = request_handler
        self._lifecycle_handler = lifecycle_handler or (lambda _error: None)
        self._next_id = 0
        self._responses: dict[int, Queue[object]] = {}
        self._responses_lock = Lock()
        self._inbound_requests: set[int] = set()
        self._inbound_tokens: dict[int, object] = {}
        self._completing_requests: set[int] = set()
        self._inbound_lock = Lock()
        self._handler_context = local()
        self._failure_lock = Lock()
        self._write_lock = RLock()
        self._closed = Event()
        self._failure: AcpTransportError | None = None
        Thread(target=self._read, daemon=True).start()
        Thread(target=self._drain_stderr, daemon=True).start()

    def request(self, method: str, params: dict, timeout: float = 5) -> object:
        response_queue: Queue[object] = Queue(maxsize=1)
        with self._write_lock:
            with self._failure_lock:
                self._raise_if_closed()
                self._next_id += 1
                request_id = self._next_id
                with self._responses_lock:
                    self._responses[request_id] = response_queue
            try:
                self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            except Exception:
                self._remove_response(request_id)
                raise
        try:
            response = response_queue.get(timeout=timeout)
        except Empty as error:
            raise ValueError("ACP request timed out") from error
        finally:
            self._remove_response(request_id)
        if isinstance(response, AcpTransportError):
            raise response
        if not isinstance(response, dict):
            raise AcpTransportError("ACP transport returned an invalid response")
        if "error" in response:
            raise ValueError("ACP request failed")
        return response.get("result")

    def respond(self, request_id: object, result: dict) -> None:
        if type(request_id) is not int:
            raise ValueError("ACP request id must be an integer")
        token = getattr(self._handler_context, "token", None)
        self._complete_inbound(request_id, {"result": result}, token)

    def respond_error(self, request_id: object, code: int, message: str) -> None:
        if type(request_id) is not int:
            raise ValueError("ACP request id must be an integer")
        if type(code) is not int or not isinstance(message, str):
            raise ValueError("ACP error response is invalid")
        error = {"code": code, "message": _safe_error_message(code)}
        token = getattr(self._handler_context, "token", None)
        self._complete_inbound(request_id, {"error": error}, token)

    def close(self) -> None:
        self._fail(AcpTransportError("ACP transport closed"))

    def _read(self) -> None:
        assert self._process.stdout is not None
        try:
            while raw := self._process.stdout.readline(_MAX_MESSAGE_BYTES + 1):
                if len(raw) > _MAX_MESSAGE_BYTES:
                    self._fail(AcpTransportError("ACP transport message exceeded limit"))
                    return
                message = _decode_message(raw)
                if message is None:
                    continue
                if "id" in message and "method" not in message:
                    self._deliver_response(message)
                elif "id" in message:
                    self._receive_request(message)
                else:
                    self._notification_handler(message)
        except Exception:
            self._fail(AcpTransportError("ACP transport read failed"))
            return
        self._fail(AcpTransportError(self._eof_message()))

    def _deliver_response(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        invalid = message.get("jsonrpc") != "2.0" or type(request_id) is not int
        if invalid or ("result" in message) == ("error" in message):
            return
        with self._responses_lock:
            response = self._responses.get(request_id)
        if response is not None:
            try:
                response.put_nowait(message)
            except Full:
                pass

    def _receive_request(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        error = _request_error(message)
        if type(request_id) is not int:
            self._write_error(None, *error)
            return
        token = Event()
        with self._failure_lock:
            if self._failure is not None:
                return
            with self._inbound_lock:
                if request_id in self._inbound_requests:
                    return
                rejection = error or (
                    (-32000, "Server busy")
                    if len(self._inbound_requests) >= _MAX_INBOUND_REQUESTS else None
                )
                if rejection is None:
                    self._inbound_requests.add(request_id)
                    self._inbound_tokens[request_id] = token
        if rejection is not None:
            self._write_error(request_id, *rejection)
        else:
            Thread(target=self._handle_request, args=(message, token), daemon=True).start()

    def _handle_request(self, message: dict[str, Any], token: object) -> None:
        request_id = message["id"]
        with self._failure_lock:
            with self._inbound_lock:
                if self._failure is not None or self._inbound_tokens.get(request_id) is not token:
                    return
                token.set()
        self._handler_context.token = token
        try:
            self._request_handler(self, message)
        except Exception:
            pass
        finally:
            try:
                self.respond_error(message["id"], -32603, "Internal error")
            except (AcpTransportError, ValueError):
                pass
            self._discard_inbound(request_id, token)
    def _complete_inbound(self, request_id: int, body: dict[str, Any], token: object | None) -> None:
        value = {"jsonrpc": "2.0", "id": request_id, **body}
        encoded = _encode_message(value)
        with self._inbound_lock:
            active = request_id in self._inbound_requests
            current = self._inbound_tokens.get(request_id)
            if not active or (current is not None and current is not token):
                raise ValueError("ACP request is not pending")
            if request_id in self._completing_requests:
                raise ValueError("ACP request is not pending")
            self._completing_requests.add(request_id)
        try:
            with self._write_lock:
                self._raise_if_closed()
                self._write_encoded(encoded)
        finally:
            self._discard_inbound(request_id, token)

    def _discard_inbound(self, request_id: int, token: object | None = None) -> None:
        with self._inbound_lock:
            current = self._inbound_tokens.get(request_id)
            if token is not None and current is not token:
                return
            self._inbound_requests.discard(request_id)
            self._inbound_tokens.pop(request_id, None)
            self._completing_requests.discard(request_id)

    def _write_error(self, request_id: int | None, code: int, message: str) -> None:
        with self._write_lock:
            self._raise_if_closed()
            error = {"code": code, "message": message}
            self._write({"jsonrpc": "2.0", "id": request_id, "error": error})

    def _drain_stderr(self) -> None:
        stream = self._process.stderr
        if stream is None:
            return
        try:
            while stream.read(64 * 1024):
                pass
        except OSError:
            return

    def _write(self, value: dict) -> None:
        self._write_encoded(_encode_message(value))

    def _write_encoded(self, encoded: bytes) -> None:
        if self._process.stdin is None:
            error = AcpTransportError("ACP stdin is unavailable")
            self._fail(error)
            raise error
        try:
            self._process.stdin.write(encoded)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            transport_error = AcpTransportError("ACP transport write failed")
            self._fail(transport_error)
            raise transport_error from error

    def _raise_if_closed(self) -> None:
        if self._failure is not None:
            raise self._failure

    def _remove_response(self, request_id: int) -> None:
        with self._responses_lock:
            self._responses.pop(request_id, None)

    def _fail(self, error: AcpTransportError) -> None:
        with self._write_lock, self._failure_lock:
            if self._closed.is_set():
                return
            self._failure = error
            self._closed.set()
        with self._inbound_lock:
            self._inbound_requests.clear()
            self._inbound_tokens.clear()
            self._completing_requests.clear()
        with self._responses_lock:
            responses = tuple(self._responses.values())
        for response in responses:
            try:
                response.put_nowait(error)
            except Full:
                continue
        with suppress(Exception):
            self._lifecycle_handler(error)

    def _eof_message(self) -> str:
        exit_code = self._process.poll()
        if exit_code is None:
            return "ACP transport closed"
        return f"ACP transport closed with exit code {exit_code}"
def _encode_message(value: dict[str, Any]) -> bytes:
    try:
        encoded = (json.dumps(value) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("ACP response is invalid") from error
    if len(encoded) > _MAX_MESSAGE_BYTES:
        raise ValueError("ACP response exceeded limit")
    return encoded
def _safe_error_message(code: int) -> str:
    safe_messages = {-32600: "Invalid Request", -32601: "Method not found",
                     -32602: "Invalid params", -32603: "Internal error"}
    return safe_messages.get(code, "Server busy" if code == -32000 else "Request failed")
def _decode_message(raw: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None
def _request_error(message: dict[str, Any]) -> tuple[int, str] | None:
    if message.get("jsonrpc") != "2.0" or type(message.get("id")) is not int:
        return -32600, "Invalid Request"
    method = message.get("method")
    if not isinstance(method, str) or method not in _RUNTIME_REQUEST_METHODS:
        return -32601, "Method not found"
    params = message.get("params")
    if not isinstance(params, dict):
        return -32602, "Invalid params"
    try:
        encoded = json.dumps(params, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return -32602, "Invalid params"
    if len(encoded) > _MAX_PARAMS_BYTES:
        return -32602, "Invalid params"
    return None
