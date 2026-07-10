"""Targeted tests for DesktopSettingsService (M151)."""
import json
import os
import platform
import sys
import tempfile

import pytest

from bolt_core.desktop_settings import DesktopSettingsService, DEFAULT_SETTINGS


def test_default_settings_are_dark_and_chinese():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)
        status = service.get_status()

        assert status["theme"] == "dark"
        assert status["language"] == "zh-CN"
        assert status["default_workspace"] == ""
        assert status["has_api_key"] is False


def test_update_theme_persists_and_returns_status():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)

        result = service.update({"theme": "light"})

        assert result["theme"] == "light"
        assert result["language"] == "zh-CN"
        assert result["has_api_key"] is False

        # reload and verify persistence
        service2 = DesktopSettingsService(tmp)
        assert service2.get_status()["theme"] == "light"


def test_update_multiple_fields():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)

        result = service.update({
            "theme": "light",
            "language": "en-US",
            "default_workspace": "/tmp/ws",
        })

        assert result["theme"] == "light"
        assert result["language"] == "en-US"
        assert result["default_workspace"] == "/tmp/ws"


def test_api_key_operations_require_credential_lifecycle():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)
        key_path = os.path.join(tmp, ".bolt", "desktop-api-key")

        assert service.has_api_key() is False
        assert service.get_status()["has_api_key"] is False
        with pytest.raises(RuntimeError, match="credential lifecycle required"):
            service.save_api_key("synthetic-secret")
        service.delete_api_key()

        assert not os.path.exists(key_path)
        assert service.has_api_key() is False


def test_api_key_empty_is_not_written():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)

        with pytest.raises(RuntimeError, match="credential lifecycle required"):
            service.save_api_key("")
        assert service.has_api_key() is False


def test_corrupt_settings_file_falls_back_to_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        bolt_dir = os.path.join(tmp, ".bolt")
        os.makedirs(bolt_dir, exist_ok=True)
        with open(os.path.join(bolt_dir, "desktop-settings.json"), "w") as f:
            f.write("NOT VALID JSON{{{")

        service = DesktopSettingsService(tmp)
        status = service.get_status()

        assert status["theme"] == DEFAULT_SETTINGS["theme"]
        assert status["language"] == DEFAULT_SETTINGS["language"]


def test_auto_creates_bolt_dir():
    with tempfile.TemporaryDirectory() as tmp:
        # .bolt does not exist yet
        bolt_dir = os.path.join(tmp, ".bolt")
        assert not os.path.exists(bolt_dir)

        service = DesktopSettingsService(tmp)
        service.update({"theme": "light"})

        assert os.path.exists(bolt_dir)
        assert os.path.exists(os.path.join(bolt_dir, "desktop-settings.json"))
