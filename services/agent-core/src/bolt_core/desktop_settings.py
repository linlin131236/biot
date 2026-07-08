"""Desktop settings persistence service (M151).

Stores user preferences (theme, language, default workspace) in
`.bolt/desktop-settings.json` and API key in `.bolt/desktop-api-key`
with file permission 600. Never returns plaintext API key to the
renderer — only `has_api_key` boolean.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "dark",
    "language": "zh-CN",
    "default_workspace": "",
    "recent_workspaces": [],
}


@dataclass
class DesktopSettings:
    theme: str = "dark"
    language: str = "zh-CN"
    default_workspace: str = ""
    recent_workspaces: list[str] = field(default_factory=list)


class DesktopSettingsService:
    """Read/write desktop user preferences to `.bolt/` directory."""

    def __init__(self, project_dir: str | Path | None = None) -> None:
        self._bolt_dir = Path(project_dir or Path.cwd()) / ".bolt"
        self._settings_path = self._bolt_dir / "desktop-settings.json"
        self._api_key_path = self._bolt_dir / "desktop-api-key"
        self._settings = self._load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_status(self) -> dict[str, Any]:
        """Return settings summary for the renderer. Never includes plaintext key."""
        return {
            "theme": self._settings.theme,
            "language": self._settings.language,
            "default_workspace": self._settings.default_workspace,
            "recent_workspaces": list(self._settings.recent_workspaces),
            "has_api_key": self._api_key_path.exists() and self._api_key_path.read_text().strip() != "",
        }

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update theme / language / default_workspace. Returns new status."""
        if "theme" in payload:
            self._settings.theme = str(payload["theme"])
        if "language" in payload:
            self._settings.language = str(payload["language"])
        if "default_workspace" in payload:
            self._settings.default_workspace = str(payload["default_workspace"])
        self._save()
        return self.get_status()

    def add_recent_workspace(self, path: str) -> dict[str, Any]:
        """Add a workspace to the recent list (deduplicated, max 10)."""
        path = str(path)
        recent = list(self._settings.recent_workspaces)
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._settings.recent_workspaces = recent[:10]
        self._save()
        return self.get_status()

    def save_api_key(self, api_key: str) -> None:
        """Persist API key with file permission 600. Key is never logged."""
        self._ensure_bolt_dir()
        self._api_key_path.write_text(api_key)
        try:
            os.chmod(self._api_key_path, 0o600)
        except OSError:
            pass
        logger.info("desktop API key saved")

    def delete_api_key(self) -> None:
        """Remove stored API key."""
        if self._api_key_path.exists():
            self._api_key_path.unlink()
            logger.info("desktop API key deleted")

    def has_api_key(self) -> bool:
        return self._api_key_path.exists() and self._api_key_path.read_text().strip() != ""

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load(self) -> DesktopSettings:
        if not self._settings_path.exists():
            return DesktopSettings()
        try:
            data = json.loads(self._settings_path.read_text())
            return DesktopSettings(
                theme=str(data.get("theme", DEFAULT_SETTINGS["theme"])),
                language=str(data.get("language", DEFAULT_SETTINGS["language"])),
                default_workspace=str(data.get("default_workspace", "")),
                recent_workspaces=[str(p) for p in data.get("recent_workspaces", [])],
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("desktop settings load fallback: %s", exc)
            return DesktopSettings()

    def _save(self) -> None:
        self._ensure_bolt_dir()
        data = {
            "theme": self._settings.theme,
            "language": self._settings.language,
            "default_workspace": self._settings.default_workspace,
            "recent_workspaces": self._settings.recent_workspaces,
        }
        self._settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        logger.info("desktop settings saved: theme=%s language=%s has_workspace=%s", data["theme"], data["language"], bool(data["default_workspace"]))

    def _ensure_bolt_dir(self) -> None:
        self._bolt_dir.mkdir(parents=True, exist_ok=True)
