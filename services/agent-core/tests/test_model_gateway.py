from bolt_core.model_gateway import (
    DefaultModelGateway,
    FakeModelGateway,
    ModelConfig,
    ModelMessage,
    ModelRequest,
    OpenAICompatibleGateway,
    ToolCall,
)
from bolt_core.workspace_credential_gate import CredentialGateError, CredentialLease, LockedWorkspace


def test_fake_gateway_returns_tool_calls_and_usage():
    gateway = FakeModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "read package")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert response.content is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "file.read"
    assert "path" in response.tool_calls[0].arguments
    assert response.usage.total_tokens > 0


def test_fake_gateway_write_returns_write_tool_call():
    gateway = FakeModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "write file")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "file.write"


def test_fake_gateway_shell_returns_shell_tool_call():
    gateway = FakeModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "run shell command")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "shell.execute"


def test_fake_gateway_uses_shared_operation_registry_for_patch(monkeypatch):
    import bolt_core.model_gateway as model_gateway

    def fake_patch_call(prompt):
        return ToolCall("call_patch", "file.patch", {"path": "README.md", "old_string": "a", "new_string": "b"})

    monkeypatch.setattr(model_gateway, "_fake_tool_call", fake_patch_call)
    gateway = FakeModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "patch README")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert '"operation": "patch"' in response.content


def test_real_gateway_fails_without_api_key():
    from bolt_core.model_gateway import OpenAICompatibleGateway

    gateway = OpenAICompatibleGateway()
    config = ModelConfig("openai", "https://api.openai.com/v1", None, "gpt-4o")
    request = ModelRequest([ModelMessage("user", "hello")], config)

    response = gateway.complete(request)

    assert response.status == "failed"
    assert response.error == "api key missing"
    assert response.tool_calls == []


def test_default_gateway_does_not_use_fake_for_openai_compatible_without_key():
    from bolt_core.model_gateway import DefaultModelGateway

    gateway = DefaultModelGateway()
    config = ModelConfig("openai-compatible", "https://api.example/v1", None, "gpt-test")
    request = ModelRequest([ModelMessage("user", "read README")], config)

    response = gateway.complete(request)

    assert response.status == "failed"
    assert response.error == "api key missing"
    assert response.tool_calls == []


def test_default_gateway_uses_fake_only_when_provider_is_fake():
    from bolt_core.model_gateway import DefaultModelGateway

    gateway = DefaultModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "read README")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert response.tool_calls[0].name == "file.read"


def test_tool_call_dataclass():
    call = ToolCall("call_123", "file.read", {"path": "/tmp/test.py"})
    assert call.id == "call_123"
    assert call.name == "file.read"
    assert call.arguments == {"path": "/tmp/test.py"}


class RecordingCredentialGate:
    def __init__(self):
        self.events: list[str] = []
        self.fail_validation = False

    def resolve(self, workspace: LockedWorkspace, provider: str) -> CredentialLease:
        self.events.append(f"resolve:{workspace.identity}:{workspace.revision}:{provider}")
        return CredentialLease("short-lived-secret", workspace.revision, 9, 7, "credential-a")

    def validate(self, workspace: LockedWorkspace, provider: str, lease: CredentialLease) -> None:
        self.events.append("validate")
        if self.fail_validation:
            raise CredentialGateError("credential_revision_changed")


class CompletedChatCompletions:
    def create(self, **_kwargs):
        message = type("Message", (), {"content": "done", "tool_calls": []})()
        choice = type("Choice", (), {"message": message})()
        return type("ProviderResponse", (), {"choices": [choice], "usage": None})()


class CompletedClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": CompletedChatCompletions()})()


def test_real_gateway_resolves_and_revalidates_before_client_construction():
    gate = RecordingCredentialGate()
    constructed: list[tuple[str, str]] = []

    def client_factory(*, base_url: str, api_key: str, timeout: float):
        gate.events.append("client")
        constructed.append((base_url, api_key))
        return CompletedClient()

    gateway = DefaultModelGateway(
        credential_gate=gate,
        real=OpenAICompatibleGateway(client_factory=client_factory),
    )
    request = ModelRequest(
        [ModelMessage("user", "hello")],
        ModelConfig("openai", "https://api.openai.com/v1", None, "gpt-test"),
        locked_workspace=LockedWorkspace("workspace-a", 4),
    )

    response = gateway.complete(request)

    assert response.status == "completed"
    assert gate.events == ["resolve:workspace-a:4:openai", "validate", "client"]
    assert constructed == [("https://api.openai.com/v1", "short-lived-secret")]


def test_revision_change_blocks_provider_client_and_network():
    gate = RecordingCredentialGate()
    gate.fail_validation = True
    constructed: list[str] = []
    gateway = DefaultModelGateway(
        credential_gate=gate,
        real=OpenAICompatibleGateway(
            client_factory=lambda **_kwargs: constructed.append("client") or CompletedClient(),
        ),
    )
    request = ModelRequest(
        [ModelMessage("user", "hello")],
        ModelConfig("openai", "https://api.openai.com/v1", None, "gpt-test"),
        locked_workspace=LockedWorkspace("workspace-a", 4),
    )

    response = gateway.complete(request)

    assert response.status == "failed"
    assert response.error == "credential_revision_changed"
    assert constructed == []


def test_production_gateway_rejects_missing_server_locked_workspace():
    gateway = DefaultModelGateway(credential_gate=RecordingCredentialGate())
    request = ModelRequest(
        [ModelMessage("user", "hello")],
        ModelConfig("openai", "https://api.openai.com/v1", None, "gpt-test"),
    )

    response = gateway.complete(request)

    assert response.status == "failed"
    assert response.error == "credential_workspace_required"
