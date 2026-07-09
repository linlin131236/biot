"""End-to-end autonomous loop service."""
from __future__ import annotations

from bolt_core.orchestrator_engine import OrchestratorEngine


class AutonomousLoopService:
    """Run a bounded autonomous loop through the orchestrator.

    The loop delegates to OrchestratorEngine for the actual role pipeline.
    It still does not push, release, tag, delete, or bypass approvals.
    """

    def __init__(self, orchestrator: OrchestratorEngine | None = None) -> None:
        self._orchestrator = orchestrator or OrchestratorEngine()

    def run_loop(self, task_description: str, workspace: str, max_rounds: int = 5) -> dict:
        safe_rounds = max(1, min(int(max_rounds), 5))
        result = self._orchestrator.orchestrate(task_description, workspace, max_review_rounds=safe_rounds)

        return {
            "task_description": result.task_description,
            "workspace": workspace,
            "max_rounds": safe_rounds,
            "rounds_completed": result.rounds,
            "status": "completed" if result.final_verdict == "approved" else "needs_review",
            "verdict": result.final_verdict,
            "trace": result.trace,
            "builder_output": result.builder_output,
            "review_findings": result.review_findings,
            "proposals": result.proposals,
            "message": "自主循环已通过编排引擎完成，未执行危险操作",
        }
