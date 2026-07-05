from bolt_core.goal import Goal, GoalBuilder, GoalStatus


def test_goal_builder_structures_vague_objective():
    builder = GoalBuilder()
    goal = builder.build("fix the tests")

    assert goal.objective == "fix the tests"
    assert len(goal.criteria) > 0
    assert goal.status == GoalStatus.PENDING
    assert goal.max_steps == 100
    assert goal.max_cost == 5.0
    assert goal.max_wall_time == 3600


def test_goal_builder_rejects_unauditably_vague_goal():
    builder = GoalBuilder()
    result = builder.build("do stuff")

    assert result.status == GoalStatus.REJECTED
    assert "vague" in result.rejection_reason.lower() or "unaudit" in result.rejection_reason.lower()


def test_goal_builder_with_explicit_criteria():
    builder = GoalBuilder()
    goal = builder.build("fix login bug", criteria=["all tests pass", "login works"])

    assert goal.criteria == ["all tests pass", "login works"]
    assert goal.status == GoalStatus.PENDING


def test_goal_builder_custom_budgets():
    builder = GoalBuilder()
    goal = builder.build("refactor module", max_steps=50, max_cost=2.0, max_wall_time=1800)

    assert goal.max_steps == 50
    assert goal.max_cost == 2.0
    assert goal.max_wall_time == 1800


def test_goal_lifecycle_transitions():
    goal = GoalBuilder().build("fix tests", criteria=["tests pass"])

    assert goal.status == GoalStatus.PENDING
    goal = goal.with_status(GoalStatus.RUNNING)
    assert goal.status == GoalStatus.RUNNING
    goal = goal.with_status(GoalStatus.PAUSED)
    assert goal.status == GoalStatus.PAUSED
    goal = goal.with_status(GoalStatus.RUNNING)
    assert goal.status == GoalStatus.RUNNING
    goal = goal.with_status(GoalStatus.COMPLETED)
    assert goal.status == GoalStatus.COMPLETED


def test_goal_cannot_transition_from_completed():
    goal = GoalBuilder().build("fix tests", criteria=["tests pass"])
    goal = goal.with_status(GoalStatus.COMPLETED)

    result = goal.with_status(GoalStatus.RUNNING)
    assert result.status == GoalStatus.COMPLETED


def test_goal_cannot_transition_from_rejected():
    goal = GoalBuilder().build("do stuff")
    assert goal.status == GoalStatus.REJECTED

    result = goal.with_status(GoalStatus.RUNNING)
    assert result.status == GoalStatus.REJECTED


def test_goal_has_id_and_workspace():
    goal = GoalBuilder().build("fix tests", criteria=["tests pass"], workspace="/project/bolt")

    assert goal.id.startswith("goal_")
    assert goal.workspace == "/project/bolt"


def test_goal_persistence_save_and_load(tmp_path):
    from bolt_core.goal_persistence import GoalPersistence

    goal = GoalBuilder().build("fix tests", criteria=["tests pass"], workspace=str(tmp_path))
    goal = goal.with_status(GoalStatus.RUNNING)

    persistence = GoalPersistence(str(tmp_path / "goals"))
    persistence.save(goal)

    loaded = persistence.load(goal.id)

    assert loaded.id == goal.id
    assert loaded.objective == goal.objective
    assert loaded.status == goal.status


def test_goal_persistence_detects_file_conflicts(tmp_path):
    from bolt_core.goal_persistence import GoalPersistence

    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "app.py").write_text("original", encoding="utf-8")

    goal = GoalBuilder().build("fix tests", criteria=["tests pass"], workspace=str(workspace))
    goal = goal.with_status(GoalStatus.RUNNING)
    goal = goal.with_snapshot({"app.py": "original"})

    persistence = GoalPersistence(str(tmp_path / "goals"))
    persistence.save(goal)

    (workspace / "app.py").write_text("modified", encoding="utf-8")

    conflicts = persistence.check_conflicts(goal.id)

    assert len(conflicts) == 1
    assert "app.py" in conflicts[0]
