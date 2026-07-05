"""Provider policy: capability routing and cost constraints."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class ProviderCapability(Enum):
    CHAT = "chat"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    EMBEDDING = "embedding"
    JSON_MODE = "json_mode"


@dataclass
class ProviderPolicy:
    tier: str = "stable"  # dev | beta | stable
    max_cost_per_request: float = 1.0
    max_cost_per_day: float = 10.0


class ProviderRegistry:
    """Route provider requests by capability and policy."""

    def __init__(self) -> None:
        self._providers: dict[str, list[ProviderCapability]] = {}
        self._policies: dict[str, ProviderPolicy] = {}

    def register(self, name: str,
                 capabilities: list[ProviderCapability] | None = None,
                 policy: ProviderPolicy | None = None) -> None:
        self._providers[name] = capabilities or [ProviderCapability.CHAT]
        self._policies[name] = policy or ProviderPolicy()

    def find(self, cap: ProviderCapability) -> list[str]:
        return [name for name, caps in self._providers.items()
                if cap in caps]

    def get_policy(self, name: str) -> ProviderPolicy | None:
        return self._policies.get(name)
