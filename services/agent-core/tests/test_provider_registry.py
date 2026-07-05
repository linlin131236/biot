import os

from bolt_core.provider_registry import ProviderRegistry, ProviderEntry, BUILTIN_PROVIDERS


def test_builtin_providers_include_openai_and_ollama():
    names = list(BUILTIN_PROVIDERS.keys())
    assert "openai" in names
    assert "ollama" in names


def test_resolve_returns_config_with_env_key():
    os.environ["TEST_BOLT_KEY"] = "sk-test-123"
    try:
        entry = ProviderEntry("test", "https://api.test.com/v1", "test-model", "TEST_BOLT_KEY")
        registry = ProviderRegistry({"test": entry})
        config = registry.resolve("test")

        assert config is not None
        assert config.provider == "test"
        assert config.api_key == "sk-test-123"
        assert config.model == "test-model"
    finally:
        del os.environ["TEST_BOLT_KEY"]


def test_resolve_returns_none_for_unknown_provider():
    registry = ProviderRegistry()
    assert registry.resolve("nonexistent") is None


def test_resolve_without_env_key_returns_none_api_key():
    entry = ProviderEntry("notest", "https://api.test.com/v1", "test-model", "MISSING_KEY_12345")
    registry = ProviderRegistry({"notest": entry})
    config = registry.resolve("notest")

    assert config is not None
    assert config.api_key is None


def test_resolve_with_model_override():
    entry = ProviderEntry("test", "https://api.test.com/v1", "default-model", "TEST_KEY_999")
    registry = ProviderRegistry({"test": entry})
    config = registry.resolve("test", model="custom-model")

    assert config is not None
    assert config.model == "custom-model"


def test_list_providers():
    registry = ProviderRegistry({"alpha": ProviderEntry("alpha", "https://a.com/v1", "a", "KEY_A")})
    assert registry.list_providers() == ["alpha"]


def test_register_adds_provider():
    registry = ProviderRegistry({})
    registry.register(ProviderEntry("new", "https://new.com/v1", "new-model", "KEY_NEW"))
    assert registry.has_provider("new")


def test_has_provider():
    registry = ProviderRegistry()
    assert registry.has_provider("openai")
    assert not registry.has_provider("nonexistent")
