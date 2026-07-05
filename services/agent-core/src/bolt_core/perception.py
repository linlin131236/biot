from __future__ import annotations

from bolt_core.file_indexer import index_workspace_files
from bolt_core.intent_router import classify_intent
from bolt_core.perception_types import RuntimeObservation, SchedulerDecision, UiObservation, PerceptionSnapshot
from bolt_core.workspace_scanner import scan_workspace


class RuntimeObserver:
    def observe(self) -> RuntimeObservation:
        return RuntimeObservation()


class UiObserver:
    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    def observe(self) -> UiObservation:
        return UiObservation(workspace_path=self.workspace)


class PerceptionService:
    def __init__(self, workspace: str) -> None:
        self.workspace = workspace
        self.runtime = RuntimeObserver()
        self.ui = UiObserver(workspace)

    def snapshot(self, goal: str, p0_context: dict[str, list]) -> PerceptionSnapshot:
        profile = scan_workspace(self.workspace)
        intent = classify_intent(goal)
        file_index = index_workspace_files(self.workspace)
        runtime = self.runtime.observe()
        ui = self.ui.observe()
        scheduler = schedule_perception(intent.category, p0_context, file_index.truncated)
        return PerceptionSnapshot(profile, file_index, intent, runtime, ui, scheduler)


def schedule_perception(intent: str, p0_context: dict[str, list], truncated: bool) -> list[SchedulerDecision]:
    p0_status = "active" if p0_context.get("hard_constraints") else "clear"
    p2_status = "truncated" if truncated else "executed"
    return [
        SchedulerDecision("P0", "safety_context", p0_status),
        SchedulerDecision("P1", f"intent:{intent}", "executed"),
        SchedulerDecision("P1", "workspace_profile", "executed"),
        SchedulerDecision("P2", "file_index", p2_status),
        SchedulerDecision("P3", "manual_observers", "manual"),
    ]
