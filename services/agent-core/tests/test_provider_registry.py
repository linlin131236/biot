from bolt_core.provider_registry import ProviderRegistry, ProviderEntry, BUILTIN_PROVIDERS


def test_builtin_providers_include_openai_and_ollama():
    names = list(BUILTIN_PROVIDERS.keys())
    assert "openai" in names
    assert "ollama" in names


def test_resolve_returns_non_secret_config_without_environment_key_lookup(monkeypatch):
    monkeypatch.setenv("TEST_BOLT_KEY", "sk-test-123")
    entry = ProviderEntry("test", "https://api.test.com/v1", "test-model", "TEST_BOLT_KEY")
    config = ProviderRegistry({"test": entry}).resolve("test")

    assert config is not None
    assert config.provider == "test"
    assert config.credential_id is None
    assert not hasattr(config, "api_key")
    assert config.model == "test-model"


def test_resolve_returns_none_for_unknown_provider():
    registry = ProviderRegistry()
    assert registry.resolve("nonexistent") is None


def test_resolve_never_exposes_an_api_key_field():
    entry = ProviderEntry("notest", "https://api.test.com/v1", "test-model", "MISSING_KEY_12345")
    registry = ProviderRegistry({"notest": entry})
    config = registry.resolve("notest")

    assert config is not None
    assert not hasattr(config, "api_key")


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
