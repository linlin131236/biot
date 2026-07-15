"""Core-only adapter from saved model profiles to the model gateway."""

from __future__ import annotations

from typing import Protocol

from bolt_core.model_gateway import ModelConfig, ModelMessage, ModelRequest
from bolt_core.workspace_credential_gate import LockedWorkspace

_MAX_MESSAGE_BYTES = 32 * 1024


class ProfileGenerationMismatchError(RuntimeError):
    pass


class ModelProfileRepository(Protocol):
    def load_model_profile(self, profile_id: str) -> dict: ...


class SavedProfileModelGateway:
    def __init__(self, profiles: ModelProfileRepository, gateway, workspace: LockedWorkspace) -> None:
        self._profiles = profiles
        self._gateway = gateway
        self._workspace = workspace

    def complete(self, profile_id: str, request: dict) -> dict:
        profile = self._load_profile(profile_id)
        expected_generation = request.get("generation") if isinstance(request, dict) else None
        actual_generation = profile.get("revision")
        if expected_generation is not None and expected_generation != actual_generation:
            raise ProfileGenerationMismatchError("model_profile_generation_changed")
        messages = _messages(request)
        response = self._gateway.complete(ModelRequest(messages, _config(profile), self._workspace))
        if response.status != "completed":
            raise RuntimeError("provider_error")
        return _response(response)

    def _load_profile(self, profile_id: str) -> dict:
        try:
            profile = self._profiles.load_model_profile(profile_id)
        except Exception as error:
            raise RuntimeError("model_not_found") from error
        if not isinstance(profile, dict):
            raise RuntimeError("model_not_found")
        return profile


def _config(profile: dict) -> ModelConfig:
    try:
        return ModelConfig(
            profile["provider"], profile["base_url"], profile.get("credential_id"),
            profile["model"], profile["temperature"], profile["timeout"], profile["context_window"],
        )
    except (KeyError, TypeError) as error:
        raise RuntimeError("model_not_found") from error


def _messages(request: object) -> list[ModelMessage]:
    payload = request.get("payload") if isinstance(request, dict) else None
    raw = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(raw, list) or not raw:
        raise ValueError("runtime model messages are required")
    messages = [_message(item) for item in raw]
    if sum(len(message.content.encode("utf-8")) for message in messages) > _MAX_MESSAGE_BYTES:
        raise ValueError("runtime model messages exceed size limit")
    return messages


def _message(value: object) -> ModelMessage:
    if not isinstance(value, dict) or set(value) != {"role", "content"}:
        raise ValueError("runtime model messages are invalid")
    if value["role"] not in {"user", "assistant"} or not isinstance(value["content"], str):
        raise ValueError("runtime model messages are invalid")
    return ModelMessage(value["role"], value["content"])


def _response(response) -> dict:
    return {
        "choices": [{"message": {"content": response.content or ""}}],
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }
