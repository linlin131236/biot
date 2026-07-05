from bolt_core.model_gateway import FakeModelGateway, ModelConfig, ModelMessage, ModelRequest
from bolt_core.model_settings import ModelSettingsStore


def test_fake_gateway_returns_tool_request_and_usage():
    gateway = FakeModelGateway()
    config = ModelConfig("fake", "http://localhost", None, "fake-model")
    request = ModelRequest([ModelMessage("user", "read package")], config)

    response = gateway.complete(request)

    assert response.status == "completed"
    assert '"tool": "file.read"' in response.content
    assert response.usage.total_tokens > 0


def test_model_settings_status_redacts_api_key():
    store = ModelSettingsStore()

    status = store.update({"provider": "openai-compatible", "base_url": "https://api.example", "api_key": "secret", "model": "test"})

    assert status.has_api_key is True
    assert "secret" not in str(status.__dict__)
    assert store.config().api_key == "secret"
