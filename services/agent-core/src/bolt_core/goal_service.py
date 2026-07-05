import os
from pathlib import Path

from bolt_core.evidence import EvidenceLog
from bolt_core.goal import Goal, GoalBuilder, GoalPersistence, GoalStatus


class GoalService:
    def __init__(self, workspace: str) -> None:
        self._workspace = workspace
        self._builder = GoalBuilder()
        goals_dir = os.path.join(workspace, ".bolt", "goals")
        self._persistence = GoalPersistence(goals_dir)
        self._goals: dict[str, Goal] = {}
        self._evidence_logs: dict[str, EvidenceLog] = {}

    def create_goal(self, payload: dict) -> Goal:
        objective = str(payload.get("objective", ""))
        criteria = payload.get("criteria")
        constraints = payload.get("constraints")
        workspace = str(payload.get("workspace", self._workspace))
        max_steps = int(payload.get("max_steps", 100))
        max_cost = float(payload.get("max_cost", 5.0))
        max_wall_time = int(payload.get("max_wall_time", 3600))
        goal = self._builder.build(
            objective, criteria=criteria, constraints=constraints,
            workspace=workspace, max_steps=max_steps, max_cost=max_cost,
            max_wall_time=max_wall_time,
        )
        if goal.status != GoalStatus.REJECTED:
            goal = goal.with_status(GoalStatus.PENDING)
            self._persistence.save(goal)
        self._goals[goal.id] = goal
        self._evidence_logs[goal.id] = EvidenceLog()
        return goal

    def get_goal(self, goal_id: str) -> Goal:
        if goal_id in self._goals:
            return self._goals[goal_id]
        goal = self._persistence.load(goal_id)
        self._goals[goal_id] = goal
        if goal_id not in self._evidence_logs:
            self._evidence_logs[goal_id] = EvidenceLog()
        return goal

    def pause_goal(self, goal_id: str) -> Goal:
        goal = self.get_goal(goal_id).with_status(GoalStatus.PAUSED)
        self._goals[goal_id] = goal
        self._persistence.save(goal)
        return goal

    def resume_goal(self, goal_id: str) -> Goal:
        goal = self.get_goal(goal_id)
        if goal.status != GoalStatus.PAUSED:
            return goal
        conflicts = self._persistence.check_conflicts(goal_id)
        if conflicts:
            return goal
        goal = goal.with_status(GoalStatus.RUNNING)
        self._goals[goal_id] = goal
        self._persistence.save(goal)
        return goal

    def clear_goal(self, goal_id: str) -> Goal:
        goal = self.get_goal(goal_id).with_status(GoalStatus.STOPPED)
        self._goals[goal_id] = goal
        self._persistence.save(goal)
        return goal

    def goal_evidence(self, goal_id: str) -> list:
        log = self._evidence_logs.get(goal_id)
        return log.entries if log else []

    def goal_budget(self, goal_id: str) -> dict:
        goal = self.get_goal(goal_id)
        log = self._evidence_logs.get(goal_id)
        steps_used = len(log.entries) if log else 0
        return {
            "goal_id": goal_id,
            "max_steps": goal.max_steps,
            "steps_used": steps_used,
            "max_cost": goal.max_cost,
            "max_wall_time": goal.max_wall_time,
        }

    def unfinished_goals(self) -> list[Goal]:
        persisted = self._persistence.list_unfinished()
        active = [g for g in self._goals.values() if g.status in (GoalStatus.PENDING, GoalStatus.RUNNING, GoalStatus.PAUSED)]
        seen = {g.id for g in active}
        for g in persisted:
            if g.id not in seen:
                active.append(g)
        return active

    def evidence_log(self, goal_id: str) -> EvidenceLog:
        if goal_id not in self._evidence_logs:
            self._evidence_logs[goal_id] = EvidenceLog()
        return self._evidence_logs[goal_id]
