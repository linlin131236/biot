from bolt_core.model_gateway import FakeModelGateway, ModelConfig, ModelMessage, ModelRequest, ToolCall


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


def test_real_gateway_fails_without_api_key():
    from bolt_core.model_gateway import OpenAICompatibleGateway

    gateway = OpenAICompatibleGateway()
    config = ModelConfig("openai", "https://api.openai.com/v1", None, "gpt-4o")
    request = ModelRequest([ModelMessage("user", "hello")], config)

    response = gateway.complete(request)

    assert response.status == "failed"
    assert response.error == "api key missing"
    assert response.tool_calls == []


def test_tool_call_dataclass():
    call = ToolCall("call_123", "file.read", {"path": "/tmp/test.py"})
    assert call.id == "call_123"
    assert call.name == "file.read"
    assert call.arguments == {"path": "/tmp/test.py"}
