"""Strict ACP request bridge to Core-owned runtime model authority."""

from __future__ import annotations

from typing import Callable

from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.model_access import RuntimeModelPolicy
from bolt_core.runtime.model_rpc import RuntimeModelRpc, RuntimeModelRpcError


class HermesModelBridge:
    def __init__(
        self,
        rpc: RuntimeModelRpc,
        policy_factory: Callable[[RuntimeSession], RuntimeModelPolicy],
    ) -> None:
        self._rpc = rpc
        self._policy_factory = policy_factory

    def register(self, session: RuntimeSession) -> RuntimeModelPolicy:
        policy = self._policy_factory(session)
        self._rpc.register(session, policy)
        return policy

    def revoke(self, session: RuntimeSession) -> None:
        self._rpc.revoke(session)

    def handle(self, client, message: dict, resolve_session: Callable[[object], RuntimeSession | None]) -> bool:
        if message.get("method") != "_bolt/model.complete":
            return False
        request_id = message.get("id")
        params = message.get("params")
        if type(request_id) is not int or not isinstance(params, dict) or set(params) != {"sessionId", "payload"}:
            client.respond_error(request_id, -32602, "Invalid params")
            return True
        session = resolve_session(params["sessionId"])
        if session is None:
            client.respond_error(request_id, -32602, "Invalid params")
            return True
        try:
            response = self._rpc.complete(session, params["payload"])
        except (RuntimeModelRpcError, ValueError):
            client.respond_error(request_id, -32000, "Model request rejected")
            return True
        client.respond(request_id, response)
        return True
