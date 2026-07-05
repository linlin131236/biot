from dataclasses import dataclass

from bolt_core.model_gateway import ModelConfig


@dataclass(frozen=True)
class ModelSettingsStatus:
    provider: str
    base_url: str
    model: str
    temperature: float
    has_api_key: bool


class ModelSettingsStore:
    def __init__(self) -> None:
        self._config = ModelConfig("fake", "http://localhost", None, "fake-model", 0.2, 120.0)

    def config(self) -> ModelConfig:
        return self._config

    def update(self, payload: dict) -> ModelSettingsStatus:
        self._config = ModelConfig(
            provider=str(payload.get("provider", self._config.provider)),
            base_url=str(payload.get("base_url", self._config.base_url)),
            api_key=payload.get("api_key") or self._config.api_key,
            model=str(payload.get("model", self._config.model)),
            temperature=float(payload.get("temperature", self._config.temperature)),
            timeout=float(payload.get("timeout", self._config.timeout)),
        )
        return self.status()

    def status(self) -> ModelSettingsStatus:
        return ModelSettingsStatus(
            self._config.provider,
            self._config.base_url,
            self._config.model,
            self._config.temperature,
            self._config.api_key is not None,
        )
