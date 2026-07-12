from dataclasses import dataclass
import sqlite3

from bolt_core.model_gateway import ModelConfig
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    PersistenceConflictError,
)


class ModelSettingsConflictError(RuntimeError):
    """A settings window attempted to overwrite a newer model profile."""


@dataclass(frozen=True)
class ModelSettingsStatus:
    provider: str
    base_url: str
    model: str
    temperature: float
    has_api_key: bool
    revision: int | None = None
    credential_id: str | None = None
    context_window: int = 8192
    capability_overrides: dict[str, bool] | None = None
    state: str = "unconfigured"
    blocked_reason: str | None = None


class ModelSettingsStore:
    PROFILE_ID = "default"

    def __init__(
        self,
        repository: ControlPlaneRepository | None = None,
        credential_store=None,
    ) -> None:
        self._repository = repository
        self._credential_store = credential_store
        self._revision: int | None = None
        self._config = ModelConfig(
            "openai-compatible", "https://api.openai.com/v1", None, "gpt-4o", 0.2, 120.0,
        )
        if repository is not None:
            self._load_persisted()

    def config(self) -> ModelConfig:
        return self._config

    def update(self, payload: dict) -> ModelSettingsStatus:
        _validate_persisted_payload(payload)
        if self._repository is None:
            self._config = ModelConfig(
                provider=str(payload.get("provider", self._config.provider)),
                base_url=str(payload.get("base_url", self._config.base_url)),
                credential_id=self._config.credential_id,
                model=str(payload.get("model", self._config.model)),
                temperature=float(payload.get("temperature", self._config.temperature)),
                timeout=float(payload.get("timeout", self._config.timeout)),
            )
            return self.status()
        return self._update_persisted(payload)

    def delete(self, *, revision: int) -> None:
        if self._repository is None:
            self._reset()
            return
        try:
            self._repository.delete_model_profile(self.PROFILE_ID, revision)
        except PersistenceConflictError as error:
            raise ModelSettingsConflictError("model settings revision conflict") from error
        self._reset()

    def status(self) -> ModelSettingsStatus:
        credential_available = self._credential_available()
        blocked = self._config.credential_id is not None and not credential_available
        return ModelSettingsStatus(
            self._config.provider,
            self._config.base_url,
            self._config.model,
            self._config.temperature,
            credential_available,
            self._revision,
            self._config.credential_id,
            self._config.context_window,
            self._config.capability_overrides or {},
            "blocked" if blocked else ("ready" if credential_available else "unconfigured"),
            "credential_not_found" if blocked else None,
        )

    def _update_persisted(self, payload: dict) -> ModelSettingsStatus:
        if type(payload.get("revision")) is not int:
            raise ValueError("model settings revision is required")
        previous_config, previous_revision = self._config, self._revision
        profile = _profile_from_config(self._config, payload)
        expected = _config_from_profile(profile)
        if self._revision is None:
            self._create_profile(payload["revision"], profile)
        else:
            self._update_profile(payload["revision"], _profile_changes(payload))
        self._load_persisted()
        if self._config != expected:
            self._restore_profile(previous_config, previous_revision)
            raise RuntimeError("model settings readback mismatch")
        return self.status()

    def _create_profile(self, revision: int, profile: dict) -> None:
        if revision != 0:
            raise ModelSettingsConflictError("model settings revision conflict")
        try:
            self._repository.save_model_profile(self.PROFILE_ID, None, **profile)
        except sqlite3.IntegrityError as error:
            raise ModelSettingsConflictError("model settings revision conflict") from error

    def _update_profile(self, revision: int, changes: dict) -> None:
        try:
            self._repository.update_model_profile(self.PROFILE_ID, revision, changes)
        except PersistenceConflictError as error:
            raise ModelSettingsConflictError("model settings revision conflict") from error

    def _restore_profile(self, config: ModelConfig, revision: int | None) -> None:
        self._config, self._revision = config, revision
        if revision is None:
            try:
                self._repository.delete_model_profile(self.PROFILE_ID, 0)
            except PersistenceConflictError as error:
                self._load_persisted()
                raise ModelSettingsConflictError("model settings readback recovery conflict") from error
            return
        try:
            self._repository.update_model_profile(
                self.PROFILE_ID, revision + 1, _profile_from_config(config, {}),
            )
        except PersistenceConflictError as error:
            self._load_persisted()
            raise ModelSettingsConflictError("model settings readback recovery conflict") from error

    def _load_persisted(self) -> None:
        try:
            profile = self._repository.load_model_profile(self.PROFILE_ID)
        except KeyError:
            return
        self._revision = profile["revision"]
        self._config = _config_from_profile(profile)

    def _credential_available(self) -> bool:
        if self._config.credential_id is None or self._credential_store is None:
            return False
        try:
            return self._credential_store.load(self._config.credential_id) is not None
        except Exception:
            return False

    def _reset(self) -> None:
        self._revision = None
        self._config = ModelConfig(
            "openai-compatible", "https://api.openai.com/v1", None, "gpt-4o", 0.2, 120.0,
        )


def _config_from_profile(profile: dict) -> ModelConfig:
    config = profile["config"]
    return ModelConfig(
        profile["provider"],
        profile["base_url"],
        profile["credential_id"],
        profile["model"],
        profile["temperature"],
        profile["timeout"],
        profile["context_window"],
        config.get("capability_overrides", {}),
    )


def _profile_from_config(config: ModelConfig, payload: dict) -> dict:
    changes = _profile_changes(payload)
    return {
        "provider": changes.get("provider", config.provider),
        "base_url": changes.get("base_url", config.base_url),
        "model": changes.get("model", config.model),
        "temperature": changes.get("temperature", config.temperature),
        "timeout": changes.get("timeout", config.timeout),
        "context_window": changes.get("context_window", config.context_window),
        "credential_id": changes.get("credential_id", config.credential_id),
        "config": changes.get(
            "config", {"capability_overrides": config.capability_overrides or {}},
        ),
    }


def _validate_persisted_payload(payload: dict) -> None:
    allowed = {
        "revision", "provider", "base_url", "model", "temperature", "timeout",
        "context_window", "credential_id", "capability_overrides",
    }
    if not isinstance(payload, dict):
        raise ValueError("unsupported model settings field")
    normalized = {key.replace("_", "").casefold() for key in payload if isinstance(key, str)}
    if normalized & {"apikey", "secret", "token", "bearer", "authorization"}:
        raise ValueError("sensitive model settings fields are not accepted")
    if set(payload) - allowed:
        raise ValueError("unsupported model settings field")


def _profile_changes(payload: dict) -> dict:
    allowed = {
        "provider", "base_url", "model", "temperature", "timeout", "context_window", "credential_id",
    }
    changes = {key: payload[key] for key in allowed & payload.keys()}
    if "capability_overrides" in payload:
        changes["config"] = {"capability_overrides": _validate_capability_overrides(payload["capability_overrides"])}
    return changes


def _validate_capability_overrides(value: object) -> dict[str, bool]:
    if not isinstance(value, dict) or any(
        not isinstance(name, str) or type(enabled) is not bool
        for name, enabled in value.items()
    ):
        raise ValueError("invalid capability overrides")
    return dict(value)
