import time
from unittest.mock import MagicMock

from bolt_core.evidence import EvidenceLog
from bolt_core.goal import Goal, GoalBuilder, GoalStatus
from bolt_core.goal_runner import GoalRunner, GoalRunnerResult


def test_goal_runner_completes_simple_goal():
    goal = GoalBuilder().build("read readme", criteria=["file read successfully"])
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=_make_step_fn("executed"), evidence_log=log)

    result = runner.run(goal)

    assert result.status == GoalStatus.COMPLETED
    assert len(log.entries) > 0


def test_goal_runner_stops_at_max_steps():
    call_count = 0

    def never_complete_step(goal, step_num, log):
        nonlocal call_count
        call_count += 1
        log.record(step=step_num, action="file.read", result="executed", output="reading", files_changed=[])
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
        log.record(step=step_num, action="llm.call", result="executed", output="thinking", files_changed=[])
        return {"status": "executed", "output": "expensive", "files_changed": [], "cost": 3.0}

    goal = GoalBuilder().build("expensive task", criteria=["never met"], max_steps=100, max_cost=5.0)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=expensive_step, evidence_log=log)

    result = runner.run(goal)

    assert result.status == GoalStatus.STOPPED
    assert "max_cost" in result.reason


def test_goal_runner_stops_at_max_wall_time():
    def slow_step(goal, step_num, log):
        time.sleep(0.5)
        log.record(step=step_num, action="file.read", result="executed", output="slow", files_changed=[])
        return {"status": "executed", "output": "slow", "files_changed": []}

    goal = GoalBuilder().build("slow task", criteria=["never met"], max_steps=100, max_wall_time=1)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=slow_step, evidence_log=log)

    result = runner.run(goal)

    assert result.status == GoalStatus.STOPPED
    assert "max_wall_time" in result.reason


def test_goal_runner_checks_completion_with_evidence():
    step_num = 0

    def completing_step(goal, step_num_inner, log):
        nonlocal step_num
        step_num = step_num_inner
        log.record(step=step_num_inner, action="shell.execute", result="executed", output="all tests pass", files_changed=[])
        return {"status": "executed", "output": "all tests pass", "files_changed": [], "evidence_type": "test_pass"}

    goal = GoalBuilder().build("fix tests", criteria=["tests pass"], max_steps=10)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=completing_step, evidence_log=log, completion_check_fn=_evidence_based_completion)

    result = runner.run(goal)

    assert result.status == GoalStatus.COMPLETED


def test_goal_runner_pauses_on_request():
    def pausing_step(goal, step_num, log):
        log.record(step=step_num, action="file.read", result="executed", output="need pause", files_changed=[])
        return {"status": "pending_permission", "output": "need approval", "files_changed": []}

    goal = GoalBuilder().build("read files", criteria=["file read"], max_steps=10)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=pausing_step, evidence_log=log)

    result = runner.run(goal)

    assert result.status == GoalStatus.PAUSED


def test_goal_runner_self_corrects_on_failure():
    call_count = 0

    def failing_then_succeeding_step(goal, step_num, log):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            log.record(step=step_num, action="shell.execute", result="failed", output="test failed", files_changed=[])
            return {"status": "failed", "output": "test failed", "files_changed": []}
        log.record(step=step_num, action="shell.execute", result="executed", output="tests pass", files_changed=["src/fix.py"])
        return {"status": "executed", "output": "tests pass", "files_changed": ["src/fix.py"], "evidence_type": "test_pass"}

    goal = GoalBuilder().build("fix tests", criteria=["tests pass"], max_steps=10)
    goal = goal.with_status(GoalStatus.RUNNING)
    log = EvidenceLog()
    runner = GoalRunner(step_fn=failing_then_succeeding_step, evidence_log=log, completion_check_fn=_evidence_based_completion)

    result = runner.run(goal)

    assert result.status == GoalStatus.COMPLETED
    assert call_count == 3


def _make_step_fn(status: str):
    def step(goal, step_num, log):
        log.record(step=step_num, action="file.read", result=status, output="done", files_changed=[])
        return {"status": status, "output": "done", "files_changed": [], "evidence_type": "file_read"}
    return step


def _evidence_based_completion(goal, evidence_log):
    for entry in evidence_log.entries:
        if entry.result == "executed" and "pass" in entry.output.lower():
            return True
    return False
