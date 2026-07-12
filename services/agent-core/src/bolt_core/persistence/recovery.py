"""Crash recovery scan for the unified control-plane repository.

On startup, tasks left in a non-terminal, in-flight state must be surfaced for
recovery rather than silently treated as completed. In-flight tasks are moved to
a dedicated ``recovering`` state so a human can decide how to proceed. A pending
human approval is never auto-approved: its original payload is preserved and the
task simply becomes ``recovering``.
"""

from __future__ import annotations

from bolt_core.persistence.repositories import ControlPlaneRepository

RECOVERING_STATE = "recovering"

# States that indicate a task was in flight when the process stopped.
_IN_FLIGHT_STATES = ("running", "waiting_approval")


class RecoveryScanner:
    def __init__(self, repository: ControlPlaneRepository) -> None:
        self._repository = repository

    def recover_workspace(self, workspace_id: str) -> list[dict]:
        """Surface in-flight tasks and move them to the recovering state.

        Returns every task that needs recovery attention, including tasks that
        were already recovering from a prior scan (idempotent).
        """
        self._repository.reconcile_runtime_sessions(workspace_id)
        candidates = self._repository.list_runtime_tasks(
            workspace_id, statuses=[*_IN_FLIGHT_STATES, RECOVERING_STATE]
        )
        recovered: list[dict] = []
        for task in candidates:
            if task["status"] in _IN_FLIGHT_STATES:
                # payload is left untouched (update_task keeps the current
                # payload when none is supplied), so a waiting_approval request
                # is preserved for human review and never auto-approved.
                recovered.append(
                    self._repository.update_runtime_task(
                        task["id"], task["runtime_session_id"],
                        task["revision"], RECOVERING_STATE,
                    )
                )
            else:
                # Already recovering: do not bump revision again.
                recovered.append(task)
        return recovered
