"""Core-owned temporary model access grants for managed runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime_token_store import RuntimeTokenClaims, RuntimeTokenStore

if TYPE_CHECKING:
    from bolt_core.model_proxy_server import ModelProxyServer


@dataclass(frozen=True)
class RuntimeModelPolicy:
    model_profile_id: str
    allowed_paths: tuple[str, ...]
    budget: int
    expires_at: datetime
    generation: int
    context_window: int

    def __post_init__(self) -> None:
        if type(self.context_window) is not int or self.context_window <= 0:
            raise ValueError("runtime model context window must be positive")


@dataclass(frozen=True)
class RuntimeProxyGrant:
    token: str
    proxy_url: str
    context_window: int

    def __post_init__(self) -> None:
        if not isinstance(self.token, str) or not self.token:
            raise ValueError("runtime proxy token is required")
        if not isinstance(self.proxy_url, str):
            raise ValueError("runtime proxy URL must be loopback")
        parsed = urlsplit(self.proxy_url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
            raise ValueError("runtime proxy URL must be loopback")
        if type(self.context_window) is not int or self.context_window <= 0:
            raise ValueError("runtime model context window must be positive")

    @property
    def environment(self) -> dict[str, str]:
        return {
            "BOLT_MODEL_PROXY_URL": self.proxy_url,
            "BOLT_RUNTIME_TOKEN": self.token,
            "NO_PROXY": "127.0.0.1,localhost",
        }


class RuntimeModelAccessBroker:
    def __init__(self, tokens: RuntimeTokenStore, server: "ModelProxyServer") -> None:
        self.tokens = tokens
        self._server = server

    @property
    def port(self) -> int:
        return self._server.port

    def start(self) -> None:
        self._server.start()

    def stop(self) -> None:
        self._server.stop()

    def issue(self, session: RuntimeSession, policy: RuntimeModelPolicy) -> RuntimeProxyGrant:
        if not isinstance(session, RuntimeSession):
            raise ValueError("session must be RuntimeSession")
        if not isinstance(policy, RuntimeModelPolicy):
            raise ValueError("policy must be RuntimeModelPolicy")
        token = self.tokens.issue(RuntimeTokenClaims(
            runtime_id=session.runtime_id,
            runtime_session_id=session.session_id,
            model_profile_id=policy.model_profile_id,
            allowed_paths=policy.allowed_paths,
            budget=policy.budget,
            expires_at=policy.expires_at,
            generation=policy.generation,
        ))
        return RuntimeProxyGrant(
            token, f"http://127.0.0.1:{self.port}/v1", policy.context_window,
        )

    def revoke_session(self, session: RuntimeSession) -> None:
        self.tokens.revoke_session(session.runtime_id, session.session_id)
