import time

from bolt_core.evidence import EvidenceLog
from bolt_core.goal import Goal, GoalBuilder, GoalStatus
from bolt_core.goal_runner import GoalRunner, GoalRunnerResult


def test_goal_runner_no_auto_complete_without_check():
    """Without completion_check_fn, runner should never auto-complete."""
    def step_with_evidence(goal, step_num, log):
        log.record(step=step_num, action="file.read", result="executed",
                   output="done", files_changed=[])
        return {"status": "executed", "output": "done",
                "files_changed": [], "evidence_type": "file_read"}

    goal = GoalBuilder().build("read file", criteria=["file read"], max_steps=3)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=step_with_evidence, evidence_log=log)

    result = runner.run(goal)
    # Should stop at max_steps, NOT complete via evidence_type
    assert result.status == GoalStatus.STOPPED
    assert "max_steps" in result.reason


def test_goal_runner_completes_with_explicit_check():
    goal = GoalBuilder().build("read readme", criteria=["file read successfully"])
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(
        step_fn=_make_step_fn("executed"), evidence_log=log,
        completion_check_fn=_evidence_based_completion)

    result = runner.run(goal)
    assert result.status == GoalStatus.COMPLETED
    assert len(log.entries) > 0


def test_goal_runner_stops_at_max_steps():
    call_count = 0

    def never_complete_step(goal, step_num, log):
        nonlocal call_count
        call_count += 1
        log.record(step=step_num, action="file.read", result="executed",
                   output="reading", files_changed=[])
        return {"status": "executed", "output": "still working", "files_changed": []}

    goal = GoalBuilder().build("endless task", criteria=["never met"], max_steps=3)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=never_complete_step, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.STOPPED
    assert call_count == 3
    assert "max_steps" in result.reason


def test_goal_runner_stops_at_max_cost():
    cost = 0.0

    def expensive_step(goal, step_num, log):
        nonlocal cost
        cost += 3.0
        log.record(step=step_num, action="llm.call", result="executed",
                   output="thinking", files_changed=[])
        return {"status": "executed", "output": "expensive",
                "files_changed": [], "cost": 3.0}

    goal = GoalBuilder().build("expensive task", criteria=["never met"],
                               max_steps=100, max_cost=5.0)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=expensive_step, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.STOPPED
    assert "max_cost" in result.reason


def test_goal_runner_stops_at_max_wall_time():
    def slow_step(goal, step_num, log):
        time.sleep(0.5)
        log.record(step=step_num, action="file.read", result="executed",
                   output="slow", files_changed=[])
        return {"status": "executed", "output": "slow", "files_changed": []}

    goal = GoalBuilder().build("slow task", criteria=["never met"],
                               max_steps=100, max_wall_time=1)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=slow_step, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.STOPPED
    assert "max_wall_time" in result.reason


def test_goal_runner_pauses_on_request():
    def pausing_step(goal, step_num, log):
        log.record(step=step_num, action="file.read", result="executed",
                   output="need pause", files_changed=[])
        return {"status": "pending_permission", "output": "need approval",
                "files_changed": []}

    goal = GoalBuilder().build("read files", criteria=["file read"], max_steps=10)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=pausing_step, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.PAUSED


def test_goal_runner_consecutive_failures_stops():
    """3 consecutive failures should stop the runner."""
    def always_fail(goal, step_num, log):
        log.record(step=step_num, action="shell.execute", result="failed",
                   output="error", files_changed=[])
        return {"status": "failed", "output": "error", "files_changed": []}

    goal = GoalBuilder().build("failing task", criteria=["never met"], max_steps=100)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=always_fail, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.FAILED
    assert "consecutive" in result.reason


def test_goal_runner_failure_then_success_resets_counter():
    """Success resets the consecutive failure counter."""
    call_count = 0

    def fail_then_succeed(goal, step_num, log):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 1:
            log.record(step=step_num, action="step", result="failed",
                       output="fail", files_changed=[])
            return {"status": "failed", "output": "fail", "files_changed": []}
        log.record(step=step_num, action="step", result="executed",
                   output="ok", files_changed=[])
        return {"status": "executed", "output": "ok", "files_changed": []}

    goal = GoalBuilder().build("intermittent", criteria=["never met"], max_steps=6)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=fail_then_succeed, evidence_log=log)

    result = runner.run(goal)
    # Should stop at max_steps, not from consecutive failures
    assert result.status == GoalStatus.STOPPED
    assert "max_steps" in result.reason


def test_goal_runner_default_cost_per_step():
    """Each step has a minimum cost of 0.01 even if step_fn omits cost."""
    call_count = 0

    def no_cost_step(goal, step_num, log):
        nonlocal call_count
        call_count += 1
        log.record(step=step_num, action="step", result="executed",
                   output="ok", files_changed=[])
        return {"status": "executed", "output": "ok", "files_changed": []}

    # With 5 steps * 0.01 = 0.05, and max_cost=0.04, should stop at cost
    goal = GoalBuilder().build("cost test", criteria=["never met"],
                               max_steps=100, max_cost=0.04)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=no_cost_step, evidence_log=log)

    result = runner.run(goal)
    assert result.status == GoalStatus.STOPPED
    assert "max_cost" in result.reason


def _make_step_fn(status: str):
    def step(goal, step_num, log):
        log.record(step=step_num, action="file.read", result=status,
                   output="done", files_changed=[])
        return {"status": status, "output": "done", "files_changed": []}
    return step


def _evidence_based_completion(goal, evidence_log):
    for entry in evidence_log.entries:
        if entry.result == "executed" and goal.criteria:
            return True
    return False
