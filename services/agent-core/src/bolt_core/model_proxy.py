"""Core-owned model request proxy for untrusted managed runtimes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from bolt_core.model_proxy_server import ModelProxyServer
from bolt_core.runtime_token_store import RuntimeTokenStore

_MAX_REQUEST_BYTES = 64 * 1024
_MAX_RESPONSE_BYTES = 256 * 1024
_FORBIDDEN_PAYLOAD_FIELDS = {
    "apikey", "authorization", "baseurl", "credential", "credentialid", "header", "headers", "provider", "secret", "token",
    "runtimeid", "runtimesessionid", "modelprofileid", "generation", "cost", "model",
}


class ProfileModelGateway(Protocol):
    def complete(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class ModelProxyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelProxyRequest:
    token: str
    request_id: str
    path: str
    payload: dict[str, Any]


class RuntimeModelProxy:
    """Authorize runtime model access without exposing provider credentials."""

    def __init__(self, tokens: RuntimeTokenStore, gateway: ProfileModelGateway) -> None:
        self._tokens = tokens
        self._gateway = gateway

    def complete(self, request: ModelProxyRequest) -> dict[str, Any]:
        payload = _sanitize_payload(request.payload)
        authorization = self._tokens.authorize_proxy(
            request.token, path=request.path, request_id=request.request_id,
        )
        try:
            response = self._complete_profile(
                authorization.claims.model_profile_id, authorization.claims.generation,
                request.path, payload,
            )
        except RuntimeError as error:
            if str(error) == "model_profile_generation_changed":
                self._tokens.revoke_generation(
                    authorization.claims.runtime_id,
                    authorization.claims.runtime_session_id,
                    authorization.claims.model_profile_id,
                    authorization.claims.generation,
                )
            raise
        self._tokens.assert_proxy_active(request.token)
        return response

    def complete_core_owned(
        self, *, model_profile_id: str, generation: int, path: str, payload: object,
    ) -> dict[str, Any]:
        """Run a Core-authorized request without exporting token authority."""
        return self._complete_profile(model_profile_id, generation, path, self.sanitize_payload(payload))

    @staticmethod
    def sanitize_payload(payload: object) -> dict[str, Any]:
        return _sanitize_payload(payload)

    def _complete_profile(
        self, model_profile_id: str, generation: int, path: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self._gateway.complete(
                model_profile_id,
                {
                    "path": path,
                    "payload": payload,
                    "generation": generation,
                },
            )
        except RuntimeError as error:
            raise
        return _bounded_response(response)

    def revoke(self, token: str) -> None:
        self._tokens.revoke(token)

    def revoke_session(self, runtime_id: str, runtime_session_id: str) -> None:
        self._tokens.revoke_session(runtime_id, runtime_session_id)

    def revoke_generation(
        self, runtime_id: str, runtime_session_id: str, model_profile_id: str, generation: int,
    ) -> None:
        self._tokens.revoke_generation(runtime_id, runtime_session_id, model_profile_id, generation)


def _sanitize_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("runtime model payload is not permitted")
    value = {key: item for key, item in payload.items() if _normalized(key) != "model"}
    if _contains_forbidden_field(value):
        raise ValueError("runtime model payload is not permitted")
    _bounded_json(value, _MAX_REQUEST_BYTES, "runtime model payload")
    return value


def _contains_forbidden_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(_normalized(key) in _FORBIDDEN_PAYLOAD_FIELDS or _contains_forbidden_field(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_field(item) for item in value)
    return False


def _bounded_response(response: object) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ModelProxyError("provider_error")
    _bounded_json(response, _MAX_RESPONSE_BYTES, "provider response")
    return response


def _bounded_json(value: object, limit: int, label: str) -> None:
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is invalid") from error
    if len(encoded) > limit:
        raise ValueError(f"{label} exceeds size limit")


def _normalized(name: object) -> str:
    return "".join(char for char in name.casefold() if char.isalnum()) if isinstance(name, str) else ""
