"""Thread-safe Runtime operation tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import ntpath
import posixpath
import re
import secrets
from threading import RLock
from typing import Callable


_RUNTIME_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


@dataclass(frozen=True)
class RuntimeTokenClaims:
    runtime_id: str
    runtime_session_id: str
    model_profile_id: str
    allowed_paths: tuple[str, ...]
    budget: int
    expires_at: datetime
    generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_id, str) or not _RUNTIME_ID.fullmatch(self.runtime_id):
            raise ValueError("runtime_id must be a controlled runtime identifier")
        if not isinstance(self.runtime_session_id, str) or not _IDENTIFIER.fullmatch(self.runtime_session_id):
            raise ValueError("runtime_session_id must be a stable identifier")
        if not isinstance(self.model_profile_id, str) or not _IDENTIFIER.fullmatch(self.model_profile_id):
            raise ValueError("model_profile_id must be a stable identifier")
        if not isinstance(self.allowed_paths, tuple) or not self.allowed_paths:
            raise ValueError("allowed_paths must be a non-empty tuple")
        paths = tuple(_normalize_path(path) for path in self.allowed_paths)
        if len(set(paths)) != len(paths):
            raise ValueError("allowed_paths must not contain duplicates")
        object.__setattr__(self, "allowed_paths", paths)
        if type(self.budget) is not int or self.budget < 0:
            raise ValueError("budget must be a non-negative integer")
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("generation must be a non-negative integer")


@dataclass(frozen=True)
class RuntimeTokenAuthorization:
    claims: RuntimeTokenClaims
    remaining_budget: int


class RuntimeTokenError(RuntimeError):
    pass


@dataclass
class _TokenState:
    claims: RuntimeTokenClaims
    remaining_budget: int
    request_ids: set[str] = field(default_factory=set)
    revoked: bool = False


class RuntimeTokenStore:
    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._tokens: dict[str, _TokenState] = {}
        self._revoked_sessions: set[tuple[str, str]] = set()
        self._revoked_generations: set[tuple[str, str, str, int]] = set()
        self._lock = RLock()

    def issue(self, claims: RuntimeTokenClaims) -> str:
        if not isinstance(claims, RuntimeTokenClaims):
            raise ValueError("claims must be RuntimeTokenClaims")
        with self._lock:
            if self._now() >= claims.expires_at:
                raise RuntimeTokenError("runtime_token_expired")
            if (claims.runtime_id, claims.runtime_session_id) in self._revoked_sessions:
                raise RuntimeTokenError("runtime_token_session_revoked")
            if _generation_key(claims) in self._revoked_generations:
                raise RuntimeTokenError("runtime_token_generation_revoked")
            token = secrets.token_urlsafe(32)
            while token in self._tokens:
                token = secrets.token_urlsafe(32)
            self._tokens[token] = _TokenState(claims, claims.budget)
            return token

    def authorize(
        self,
        token: str,
        *,
        runtime_id: str,
        runtime_session_id: str,
        model_profile_id: str,
        generation: int,
        path: str,
        cost: int,
        request_id: str,
    ) -> RuntimeTokenAuthorization:
        if not isinstance(token, str):
            raise RuntimeTokenError("runtime_token_invalid")
        with self._lock:
            state = self._state_for(token)
            claims = state.claims
            self._validate_active(state, claims, runtime_id, runtime_session_id)
            self._validate_operation(
                claims, runtime_id, runtime_session_id, model_profile_id, generation, path, cost, request_id,
            )
            if request_id in state.request_ids:
                raise RuntimeTokenError("runtime_token_replayed")
            if cost > state.remaining_budget:
                raise RuntimeTokenError("runtime_token_budget_exhausted")
            state.request_ids.add(request_id)
            state.remaining_budget -= cost
            return RuntimeTokenAuthorization(claims, state.remaining_budget)

    def authorize_proxy(self, token: str, *, path: str, request_id: str) -> RuntimeTokenAuthorization:
        if not isinstance(token, str):
            raise RuntimeTokenError("runtime_token_invalid")
        with self._lock:
            state = self._state_for(token)
            claims = state.claims
            self._validate_active(state, claims, claims.runtime_id, claims.runtime_session_id)
            self._validate_operation(
                claims, claims.runtime_id, claims.runtime_session_id,
                claims.model_profile_id, claims.generation, path, 1, request_id,
            )
            if request_id in state.request_ids:
                raise RuntimeTokenError("runtime_token_replayed")
            if state.remaining_budget < 1:
                raise RuntimeTokenError("runtime_token_budget_exhausted")
            state.request_ids.add(request_id)
            state.remaining_budget -= 1
            return RuntimeTokenAuthorization(claims, state.remaining_budget)

    def assert_proxy_active(self, token: str) -> RuntimeTokenClaims:
        with self._lock:
            state = self._state_for(token)
            claims = state.claims
            self._validate_active(state, claims, claims.runtime_id, claims.runtime_session_id)
            return claims

    def revoke(self, token: str) -> None:
        if not isinstance(token, str):
            raise RuntimeTokenError("runtime_token_invalid")
        with self._lock:
            try:
                self._tokens[token].revoked = True
            except KeyError as error:
                raise RuntimeTokenError("runtime_token_invalid") from error

    def revoke_session(self, runtime_id: str, runtime_session_id: str) -> None:
        with self._lock:
            self._revoked_sessions.add((runtime_id, runtime_session_id))

    def revoke_generation(
        self, runtime_id: str, runtime_session_id: str, model_profile_id: str, generation: int
    ) -> None:
        key = runtime_id, runtime_session_id, model_profile_id, generation
        with self._lock:
            self._revoked_generations.add(key)
            for state in self._tokens.values():
                if _generation_key(state.claims) == key:
                    state.revoked = True

    def _state_for(self, token: str) -> _TokenState:
        try:
            return self._tokens[token]
        except KeyError as error:
            raise RuntimeTokenError("runtime_token_invalid") from error

    def _validate_active(
        self,
        state: _TokenState,
        claims: RuntimeTokenClaims,
        runtime_id: str,
        runtime_session_id: str,
    ) -> None:
        if state.revoked or (runtime_id, runtime_session_id) in self._revoked_sessions:
            raise RuntimeTokenError("runtime_token_invalid")
        if self._now() >= claims.expires_at:
            raise RuntimeTokenError("runtime_token_expired")

    @staticmethod
    def _validate_operation(
        claims: RuntimeTokenClaims,
        runtime_id: str,
        runtime_session_id: str,
        model_profile_id: str,
        generation: int,
        path: str,
        cost: int,
        request_id: str,
    ) -> None:
        actual = runtime_id, runtime_session_id, model_profile_id, generation
        expected = claims.runtime_id, claims.runtime_session_id, claims.model_profile_id, claims.generation
        if actual != expected:
            raise RuntimeTokenError("runtime_token_binding_mismatch")
        if not _is_allowed_path(path, claims.allowed_paths):
            raise RuntimeTokenError("runtime_token_path_not_allowed")
        if type(cost) is not int or cost < 0:
            raise ValueError("cost must be a non-negative integer")
        if not isinstance(request_id, str) or not _IDENTIFIER.fullmatch(request_id):
            raise ValueError("request_id must be a stable identifier")


def _generation_key(claims: RuntimeTokenClaims) -> tuple[str, str, str, int]:
    return (
        claims.runtime_id, claims.runtime_session_id,
        claims.model_profile_id, claims.generation,
    )


def _is_allowed_path(path: str, allowed_paths: tuple[str, ...]) -> bool:
    try:
        normalized = _normalize_path(path)
    except ValueError:
        return False
    return any(_is_under_root(normalized, root) for root in allowed_paths)


def _normalize_path(path: object) -> str:
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("path must be a non-empty path")
    module = ntpath if "\\" in path or _has_windows_drive(path) else posixpath
    normalized = module.normpath(path)
    if not module.isabs(normalized):
        raise ValueError("path must be absolute")
    return normalized.casefold() if module is ntpath else normalized


def _is_under_root(path: str, root: str) -> bool:
    module = ntpath if "\\" in path or _has_windows_drive(path) else posixpath
    root_module = ntpath if "\\" in root or _has_windows_drive(root) else posixpath
    if module is not root_module:
        return False
    try:
        return module.commonpath((path, root)) == root
    except ValueError:
        return False


def _has_windows_drive(path: str) -> bool:
    return len(path) >= 2 and path[1] == ":" and path[0].isalpha()
