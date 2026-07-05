"""MoA (Mixture of Agents) orchestrator: multi-model arbitration.

Default is dry_run mode — no real API calls. Consensus records
dissent. Budget must be enforced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_SECRET_PATTERN = re.compile(r"sk-[a-zA-Z0-9]{20,}")


@dataclass(frozen=True)
class MoACandidate:
    model: str
    summary: str
    output: str


@dataclass
class MoAResult:
    selected: str | None  # model name
    output: str
    candidate_summaries: list[dict]
    dissent: str | None = None
    reason: str = ""
    cost: float = 0.0

    def to_dict(self) -> dict:
        return {
            "selected": self.selected,
            "output": self._scrub(self.output),
            "candidate_summaries": [
                {**s, "summary": self._scrub(s.get("summary", ""))}
                for s in self.candidate_summaries
            ],
            "dissent": self.dissent,
            "reason": self.reason,
            "cost": self.cost,
        }

    @staticmethod
    def _scrub(text: str) -> str:
        return _SECRET_PATTERN.sub("[REDACTED]", text)


class MoAOrchestrator:
    """Arbitrate between multiple model outputs."""

    def __init__(self, dry_run: bool = True) -> None:
        self._dry_run = dry_run

    def arbitrate(self, candidates: list[MoACandidate],
                  budget: float = 1.0) -> MoAResult:
        if budget <= 0:
            return MoAResult(
                selected=None, output="",
                candidate_summaries=[], reason="budget exhausted")

        if not candidates:
            return MoAResult(
                selected=None, output="",
                candidate_summaries=[], reason="no candidates")

        summaries = [
            {"model": c.model, "summary": c.summary}
            for c in candidates
        ]

        # Simple arbitration: pick first candidate by default
        # In real mode, would use a judge model
        selected = candidates[0]

        # Check for dissent (different approaches)
        dissent = None
        approaches = set(c.summary[:50] for c in candidates)
        if len(approaches) > 1:
            dissent = f"Candidates disagree: {len(approaches)} different approaches"

        cost = 0.01 * len(candidates) if not self._dry_run else 0.0

        return MoAResult(
            selected=selected.model,
            output=selected.output,
            candidate_summaries=summaries,
            dissent=dissent,
            cost=cost,
        )
