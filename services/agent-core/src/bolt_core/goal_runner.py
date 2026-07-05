import time
from dataclasses import dataclass

from bolt_core.evidence import EvidenceLog
from bolt_core.goal import Goal, GoalStatus

_MAX_CONSECUTIVE_FAILURES = 3


@dataclass(frozen=True)
class GoalRunnerResult:
    status: GoalStatus
    reason: str
    steps: int


class GoalRunner:
    def __init__(self, step_fn, evidence_log: EvidenceLog,
                 completion_check_fn=None) -> None:
        self._step_fn = step_fn
        self._evidence_log = evidence_log
        self._completion_check_fn = completion_check_fn

    def run(self, goal: Goal) -> GoalRunnerResult:
        if goal.status not in (GoalStatus.RUNNING, GoalStatus.PENDING):
            return GoalRunnerResult(goal.status, "goal not runnable", goal.step_count)

        start_time = time.monotonic()
        total_cost = 0.0
        step_num = goal.step_count
        consecutive_failures = 0

        while True:
            step_num += 1
            elapsed = time.monotonic() - start_time

            if step_num > goal.max_steps:
                return GoalRunnerResult(
                    GoalStatus.STOPPED, "max_steps exceeded", step_num - 1)
            if total_cost >= goal.max_cost:
                return GoalRunnerResult(
                    GoalStatus.STOPPED, "max_cost exceeded", step_num - 1)
            if elapsed >= goal.max_wall_time:
                return GoalRunnerResult(
                    GoalStatus.STOPPED, "max_wall_time exceeded", step_num - 1)

            step_result = self._step_fn(goal, step_num, self._evidence_log)
            step_cost = step_result.get("cost", 0.01)
            total_cost += step_cost

            if step_result.get("status") == "pending_permission":
                return GoalRunnerResult(
                    GoalStatus.PAUSED, "paused for permission", step_num)

            if step_result.get("status") == "failed":
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    return GoalRunnerResult(
                        GoalStatus.FAILED,
                        f"{_MAX_CONSECUTIVE_FAILURES} consecutive failures",
                        step_num)
                continue

            # Step succeeded — reset failure counter
            consecutive_failures = 0

            # Only complete via explicit completion_check_fn
            if self._completion_check_fn and \
               self._completion_check_fn(goal, self._evidence_log):
                return GoalRunnerResult(
                    GoalStatus.COMPLETED, "criteria met with evidence", step_num)

            elapsed = time.monotonic() - start_time
            if elapsed >= goal.max_wall_time:
                return GoalRunnerResult(
                    GoalStatus.STOPPED, "max_wall_time exceeded", step_num)
