"""Review gate: phase completion checklist evaluation.

Review failure blocks continuation to next phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewChecklist:
    items: list[str]


@dataclass
class ReviewResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


class ReviewGate:
    """Evaluate a checklist against recorded results."""

    def evaluate(self, checklist: ReviewChecklist,
                 results: dict[str, bool]) -> ReviewResult:
        failures = []
        for item in checklist.items:
            if not results.get(item, False):
                failures.append(item)
        return ReviewResult(passed=len(failures) == 0, failures=failures)
