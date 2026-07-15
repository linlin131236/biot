"""Core-owned model authority for managed-runtime ACP requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Callable

from bolt_core.model_proxy import RuntimeModelProxy
from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.model_access import RuntimeModelPolicy


class RuntimeModelRpcError(RuntimeError):
    pass


@dataclass
class _Authority:
    policy: RuntimeModelPolicy
    remaining_budget: int
    lock: RLock = field(default_factory=RLock)


class RuntimeModelRpc:
    """Keep model identity, credentials, and request budget inside Core."""

    def __init__(
        self, proxy: RuntimeModelProxy, now: Callable[[], datetime] | None = None,
    ) -> None:
        self._proxy = proxy
        self._now = now or (lambda: datetime.now(UTC))
        self._authorities: dict[tuple[str, str], _Authority] = {}
        self._lock = RLock()

    def register(self, session: RuntimeSession, policy: RuntimeModelPolicy) -> None:
        if not isinstance(session, RuntimeSession) or not isinstance(policy, RuntimeModelPolicy):
            raise ValueError("runtime model authority is invalid")
        if not _valid_policy(policy):
            raise ValueError("runtime model authority is invalid")
        if self._now() >= policy.expires_at:
            raise RuntimeModelRpcError("runtime_model_authority_expired")
        with self._lock:
            self._authorities[_key(session)] = _Authority(policy, policy.budget)

    def revoke(self, session: RuntimeSession) -> None:
        if not isinstance(session, RuntimeSession):
            return
        key = _key(session)
        with self._lock:
            self._authorities.pop(key, None)

    def complete(self, session: RuntimeSession, payload: object) -> dict:
        key = _key(session)
        clean_payload = self._proxy.sanitize_payload(payload)
        with self._lock:
            authority = self._active_authority(key)
            if authority.remaining_budget < 1:
                raise RuntimeModelRpcError("runtime_model_budget_exhausted")
            authority.remaining_budget -= 1
        with authority.lock:
            return self._complete_active(session, key, authority, clean_payload)

    def _complete_active(
        self, session: RuntimeSession, key: tuple[str, str], authority: _Authority, payload: dict,
    ) -> dict:
        with self._lock:
            if self._authorities.get(key) is not authority:
                raise RuntimeModelRpcError("runtime_model_authority_invalid")
            self._active_authority(key)
            policy = authority.policy
        try:
            response = self._proxy.complete_core_owned(
                model_profile_id=policy.model_profile_id,
                generation=policy.generation,
                path="/v1/chat/completions",
                payload=payload,
            )
        except RuntimeError as error:
            if str(error) == "model_profile_generation_changed":
                self.revoke(session)
                raise RuntimeModelRpcError("runtime_model_authority_invalid") from None
            raise
        with self._lock:
            if self._authorities.get(key) is not authority:
                raise RuntimeModelRpcError("runtime_model_authority_invalid")
            if self._now() >= policy.expires_at:
                self._authorities.pop(key, None)
                raise RuntimeModelRpcError("runtime_model_authority_expired")
        return response

    def _active_authority(self, key: tuple[str, str]) -> _Authority:
        authority = self._authorities.get(key)
        if authority is None:
            raise RuntimeModelRpcError("runtime_model_authority_invalid")
        if self._now() >= authority.policy.expires_at:
            self._authorities.pop(key, None)
            raise RuntimeModelRpcError("runtime_model_authority_expired")
        return authority


def _key(session: RuntimeSession) -> tuple[str, str]:
    if not isinstance(session, RuntimeSession):
        raise RuntimeModelRpcError("runtime_model_authority_invalid")
    return session.runtime_id, session.session_id


def _valid_policy(policy: RuntimeModelPolicy) -> bool:
    return (
        isinstance(policy.model_profile_id, str)
        and bool(policy.model_profile_id)
        and policy.allowed_paths == ("/v1/chat/completions",)
        and type(policy.budget) is int and policy.budget >= 0
        and type(policy.generation) is int and policy.generation >= 0
        and isinstance(policy.expires_at, datetime) and policy.expires_at.tzinfo is not None
    )
