from dataclasses import dataclass

import pytest

from bolt_core.model_gateway import ModelResponse, TokenUsage
from bolt_core.profile_model_gateway import SavedProfileModelGateway
from bolt_core.workspace_credential_gate import LockedWorkspace


@dataclass
class ProfileRepository:
    profile: dict

    def load_model_profile(self, profile_id: str) -> dict:
        if profile_id != "profile_12345678":
            raise KeyError(profile_id)
        return self.profile


class Gateway:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return ModelResponse("completed", "safe", TokenUsage(2, 3, 5), [], None)


def _profile():
    return {
        "id": "profile_12345678",
        "provider": "openai-compatible",
        "base_url": "https://api.example.test/v1",
        "credential_id": "credential_12345678",
        "model": "saved-model",
        "temperature": 0.3,
        "timeout": 30.0,
        "context_window": 8192,
        "revision": 1,
        "config": {},
    }


def test_saved_profile_gateway_uses_only_saved_profile_and_server_locked_workspace():
    gateway = Gateway()
    adapter = SavedProfileModelGateway(
        ProfileRepository(_profile()), gateway, LockedWorkspace("workspace-identity", 1),
    )

    response = adapter.complete("profile_12345678", {
        "path": "/v1/chat/completions",
        "payload": {"messages": [{"role": "user", "content": "hello"}]},
    })

    request = gateway.requests[0]
    assert request.config.provider == "openai-compatible"
    assert request.config.base_url == "https://api.example.test/v1"
    assert request.config.model == "saved-model"
    assert request.config.credential_id == "credential_12345678"
    assert request.locked_workspace == LockedWorkspace("workspace-identity", 1)
    assert response == {
        "choices": [{"message": {"content": "safe"}}],
        "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
    }


def test_saved_profile_gateway_rejects_a_stale_runtime_generation_before_provider_call():
    gateway = Gateway()
    adapter = SavedProfileModelGateway(
        ProfileRepository(_profile()), gateway, LockedWorkspace("workspace-identity", 1),
    )

    with pytest.raises(RuntimeError, match="generation_changed"):
        adapter.complete("profile_12345678", {
            "path": "/v1/chat/completions",
            "generation": 0,
            "payload": {"messages": [{"role": "user", "content": "hello"}]},
        })

    assert gateway.requests == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"messages": []},
        {"messages": [{"role": "system", "content": "forbidden"}]},
        {"messages": [{"role": "user", "content": 123}]},
        {"messages": [{"role": "user", "content": "x" * (64 * 1024)}]},
    ],
)
def test_saved_profile_gateway_rejects_untrusted_runtime_message_shapes(payload):
    adapter = SavedProfileModelGateway(
        ProfileRepository(_profile()), Gateway(), LockedWorkspace("workspace-identity", 1),
    )

    with pytest.raises(ValueError, match="runtime model messages"):
        adapter.complete("profile_12345678", {"path": "/v1/chat/completions", "payload": payload})


def test_saved_profile_gateway_does_not_leak_gateway_error_text():
    class FailedGateway:
        def complete(self, _request):
            return ModelResponse("failed", None, TokenUsage(0, 0, 0), [], "Bearer provider-secret")

    adapter = SavedProfileModelGateway(
        ProfileRepository(_profile()), FailedGateway(), LockedWorkspace("workspace-identity", 1),
    )

    with pytest.raises(RuntimeError, match="provider_error") as error:
        adapter.complete("profile_12345678", {"path": "/v1/chat/completions", "payload": {"messages": [{"role": "user", "content": "hello"}]}})

    assert "provider-secret" not in str(error.value)
