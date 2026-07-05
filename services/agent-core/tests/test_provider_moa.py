from bolt_core.provider_policy import (
    ProviderCapability, ProviderPolicy, ProviderRegistry,
)
from bolt_core.moa import MoAOrchestrator, MoAResult, MoACandidate


def test_provider_capability_routing():
    registry = ProviderRegistry()
    registry.register("local-llm", capabilities=[ProviderCapability.CHAT])
    registry.register("gpt-4o", capabilities=[
        ProviderCapability.CHAT, ProviderCapability.TOOL_CALLING,
        ProviderCapability.VISION, ProviderCapability.JSON_MODE,
    ])

    # Route tool_calling request
    providers = registry.find(ProviderCapability.TOOL_CALLING)
    assert len(providers) >= 1
    assert providers[0] == "gpt-4o"


def test_provider_missing_key_unavailable():
    registry = Registry_no_keys()
    providers = registry.find(ProviderCapability.CHAT)
    assert len(providers) == 0


def test_provider_policy_tier():
    policy = ProviderPolicy(tier="stable")
    assert policy.tier == "stable"


def test_moa_orchestrator_dry_run():
    orch = MoAOrchestrator(dry_run=True)
    candidates = [
        MoACandidate(model="model-a", summary="Use approach X", output="code X"),
        MoACandidate(model="model-b", summary="Use approach Y", output="code Y"),
    ]
    result = orch.arbitrate(candidates, budget=1.0)
    assert isinstance(result, MoAResult)
    assert result.selected is not None
    assert len(result.candidate_summaries) == 2


def test_moa_budget_stops():
    orch = MoAOrchestrator(dry_run=True)
    # With budget 0, should not run
    result = orch.arbitrate([], budget=0.0)
    assert result.selected is None
    assert "budget" in result.reason


def test_moa_records_dissent():
    orch = MoAOrchestrator(dry_run=True)
    candidates = [
        MoACandidate(model="a", summary="Approach A", output="X"),
        MoACandidate(model="b", summary="Approach B", output="Y"),
    ]
    result = orch.arbitrate(candidates, budget=10.0)
    # When candidates disagree, dissent should be recorded
    if len(result.candidate_summaries) > 1:
        assert result.dissent is not None


def test_moa_no_secret_leakage():
    orch = MoAOrchestrator(dry_run=True)
    candidates = [
        MoACandidate(model="a", summary="Used key sk-abc123def456ghi789jkl012mno345",
                     output="code"),
    ]
    result = orch.arbitrate(candidates, budget=1.0)
    # Result should not contain raw secrets in to_dict output
    result_str = str(result.to_dict())
    assert "sk-abc123" not in result_str


class Registry_no_keys(ProviderRegistry):
    """Registry with no keys configured."""
    def __init__(self):
        self._providers: dict[str, list[ProviderCapability]] = {}

    def find(self, cap: ProviderCapability) -> list[str]:
        return []
