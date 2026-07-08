from bolt_core.model_settings import ModelSettingsStore


def test_model_settings_default_is_real_provider_not_fake():
    store = ModelSettingsStore()

    status = store.status()
    config = store.config()

    assert status.provider == "openai-compatible"
    assert config.provider == "openai-compatible"
    assert config.model != "fake-model"
    assert status.has_api_key is False


def test_model_settings_can_explicitly_select_fake_for_tests():
    store = ModelSettingsStore()

    status = store.update({"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})

    assert status.provider == "fake"
    assert store.config().provider == "fake"
