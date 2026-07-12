"""Coordinates goal/task persistence onto the single source of truth.

When a ControlPlaneRepository is configured, goals are persisted exclusively
through it (tasks table). The legacy GoalService JSON files are only used when
no repository is configured (non-production / in-memory tests). No dual-write,
no fallback, no adapter shim.

Goal state-machine semantics are preserved by reusing Goal.with_status; the
repository row is the durable projection (status column + full goal dict in the
payload). Evidence and budget remain in-memory and are delegated to the legacy
GoalService because they are not a persistence truth source.
"""

from __future__ import annotations

from bolt_core.goal import Goal, GoalBuilder, GoalStatus


class GoalCoordinator:
    def __init__(self, workspace: str, persistence=None, legacy_service=None) -> None:
        self._workspace = workspace
        self._persistence = persistence
        self._legacy = legacy_service
        self._builder = GoalBuilder()
        self._workspace_id: str | None = None

    @property
    def uses_repository(self) -> bool:
        return self._persistence is not None

    def _ensure_workspace(self) -> str:
        if self._workspace_id is None:
            self._workspace_id = self._persistence.save_workspace(self._workspace)
        return self._workspace_id

    def create_goal(self, payload: dict) -> Goal:
        if not self.uses_repository:
            return self._legacy.create_goal(payload)
        goal = self._builder.build(
            str(payload.get("objective", "")),
            criteria=payload.get("criteria"),
            constraints=payload.get("constraints"),
            workspace=str(payload.get("workspace", self._workspace)),
            max_steps=int(payload.get("max_steps", 100)),
            max_cost=float(payload.get("max_cost", 5.0)),
            max_wall_time=int(payload.get("max_wall_time", 3600)),
        )
        if goal.status == GoalStatus.REJECTED:
            return goal
        goal = goal.with_status(GoalStatus.PENDING)
        workspace_id = self._ensure_workspace()
        self._persistence.create_task(
            goal.id, workspace_id, None, goal.status.value, _goal_payload(goal),
        )
        return goal

    def get_goal(self, goal_id: str) -> Goal:
        if not self.uses_repository:
            return self._legacy.get_goal(goal_id)
        return _goal_from_task(self._persistence.load_task(goal_id))

    def pause_goal(self, goal_id: str) -> Goal:
        return self._transition(goal_id, GoalStatus.PAUSED)

    def resume_goal(self, goal_id: str) -> Goal:
        if not self.uses_repository:
            return self._legacy.resume_goal(goal_id)
        current = self.get_goal(goal_id)
        if current.status != GoalStatus.PAUSED:
            return current
        return self._transition(goal_id, GoalStatus.RUNNING)

    def clear_goal(self, goal_id: str) -> Goal:
        return self._transition(goal_id, GoalStatus.STOPPED)

    def goal_evidence(self, goal_id: str) -> list:
        return self._legacy.goal_evidence(goal_id)

    def goal_budget(self, goal_id: str) -> dict:
        if not self.uses_repository:
            return self._legacy.goal_budget(goal_id)
        goal = self.get_goal(goal_id)
        log = self._legacy.evidence_log(goal_id)
        return {
            "goal_id": goal_id,
            "max_steps": goal.max_steps,
            "steps_used": len(log.entries),
            "max_cost": goal.max_cost,
            "max_wall_time": goal.max_wall_time,
        }

    def unfinished_goals(self) -> list[Goal]:
        if not self.uses_repository:
            return self._legacy.unfinished_goals()
        workspace_id = self._ensure_workspace()
        rows = self._persistence.list_tasks(
            workspace_id, statuses=["pending", "running", "paused"],
        )
        return [_goal_from_task(row) for row in rows]

    def _transition(self, goal_id: str, status: GoalStatus) -> Goal:
        if not self.uses_repository:
            method = {
                GoalStatus.PAUSED: self._legacy.pause_goal,
                GoalStatus.STOPPED: self._legacy.clear_goal,
            }[status]
            return method(goal_id)
        task = self._persistence.load_task(goal_id)
        goal = _goal_from_task(task).with_status(status)
        updated = self._persistence.update_task(
            goal_id, expected_revision=task["revision"],
            status=goal.status.value, payload=_goal_payload(goal),
        )
        return _goal_from_task(updated)


def _goal_payload(goal: Goal) -> dict:
    payload = goal.to_dict()
    payload.pop("id", None)
    payload.pop("status", None)
    return payload


def _goal_from_task(task: dict) -> Goal:
    data = dict(task["payload"])
    data["id"] = task["id"]
    data["status"] = task["status"]
    return Goal.from_dict(data)
