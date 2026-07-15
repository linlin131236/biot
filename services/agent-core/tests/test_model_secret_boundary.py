from dataclasses import fields

import pytest

from bolt_core.desktop_settings import DesktopSettingsService
from bolt_core.model_gateway import ModelConfig
from bolt_core.model_settings import ModelSettingsStore


def test_desktop_settings_never_creates_or_reads_normal_api_key_file(tmp_path):
    legacy = tmp_path / ".bolt" / "desktop-api-key"
    legacy.parent.mkdir()
    legacy.write_text("legacy-secret")
    service = DesktopSettingsService(tmp_path)

    assert service.get_status()["has_api_key"] is False
    with pytest.raises(RuntimeError, match="credential lifecycle required"):
        service.save_api_key("must-not-write")
    service.delete_api_key()
    assert legacy.read_text() == "legacy-secret"


def test_model_config_contains_only_non_secret_credential_reference():
    names = {field.name for field in fields(ModelConfig)}

    assert "api_key" not in names
    assert "capability_overrides" not in names
    assert "credential_id" in names


def test_model_settings_rejects_plaintext_api_key_payload():
    store = ModelSettingsStore()

    with pytest.raises(ValueError, match="sensitive model settings fields"):
        store.update({"api_key": "must-not-be-retained"})

    assert store.status().has_api_key is False
    assert not hasattr(store.config(), "api_key")
