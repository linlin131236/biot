"""Provider registry: resolves LLM provider configurations from environment variables.

API keys come from env or explicit user config, never from repo files.
"""

import os
from dataclasses import dataclass

from bolt_core.model_gateway import ModelConfig


@dataclass(frozen=True)
class ProviderEntry:
    name: str
    base_url: str
    model: str
    api_key_env: str
    default_temperature: float = 0.2


# Built-in provider templates. API keys are resolved from env at runtime.
BUILTIN_PROVIDERS: dict[str, ProviderEntry] = {
    "openai": ProviderEntry("openai", "https://api.openai.com/v1", "gpt-4o", "OPENAI_API_KEY"),
    "deepseek": ProviderEntry("deepseek", "https://api.deepseek.com/v1", "deepseek-chat", "DEEPSEEK_API_KEY"),
    "zyloo": ProviderEntry("zyloo", "https://api.zyloo.com/v1", "gpt-4o", "ZYLOO_API_KEY"),
    "ollama": ProviderEntry("ollama", "http://localhost:11434/v1", "llama3", "OLLAMA_API_KEY"),
}


class ProviderRegistry:
    """Registry of LLM providers. Resolves API keys from environment."""

    def __init__(self, providers: dict[str, ProviderEntry] | None = None) -> None:
        self._providers = providers or dict(BUILTIN_PROVIDERS)

    def resolve(self, name: str, model: str | None = None, temperature: float | None = None) -> ModelConfig | None:
        entry = self._providers.get(name)
        if entry is None:
            return None
        api_key = os.environ.get(entry.api_key_env)
        return ModelConfig(
            provider=entry.name,
            base_url=entry.base_url,
            api_key=api_key,
            model=model or entry.model,
            temperature=temperature if temperature is not None else entry.default_temperature,
        )

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    def register(self, entry: ProviderEntry) -> None:
        self._providers[entry.name] = entry
