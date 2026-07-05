import json
import pytest
from pathlib import Path

from bolt_core.goal import Goal, GoalBuilder, GoalStatus
from bolt_core.goal_persistence import GoalPersistence, GOAL_ID_PATTERN


def test_goal_id_pattern_valid():
    assert GOAL_ID_PATTERN.match("goal_abc12345")


def test_goal_id_pattern_rejects_traversal():
    assert not GOAL_ID_PATTERN.match("../../etc/passwd")
    assert not GOAL_ID_PATTERN.match("goal_../../etc")
    assert not GOAL_ID_PATTERN.match("")
    assert not GOAL_ID_PATTERN.match("goal_SHORT")


def test_goal_id_pattern_rejects_spaces():
    assert not GOAL_ID_PATTERN.match("goal_abc 1234")


def test_persistence_save_and_load(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    goal = Goal(objective="test goal", criteria=["pass tests"])
    p.save(goal)

    loaded = p.load(goal.id)
    assert loaded.objective == "test goal"
    assert loaded.criteria == ["pass tests"]


def test_persistence_load_invalid_id_fail_closed(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    with pytest.raises(ValueError, match="Invalid goal_id"):
        p.load("../../etc/passwd")


def test_persistence_save_invalid_id_fail_closed(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    goal = Goal(id="bad_id", objective="test")
    with pytest.raises(ValueError, match="Invalid goal_id"):
        p.save(goal)


def test_persistence_load_corrupt_json(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    goal = Goal(objective="test")
    p.save(goal)

    # Corrupt the file
    goal_path = tmp_path / "goals" / f"{goal.id}.json"
    goal_path.write_text("{corrupt json", encoding="utf-8")

    with pytest.raises(ValueError, match="corrupt"):
        p.load(goal.id)


def test_persistence_load_missing(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    with pytest.raises(FileNotFoundError):
        p.load("goal_aabbccdd")


def test_persistence_atomic_write(tmp_path):
    """Save uses temp file + rename for atomicity."""
    p = GoalPersistence(str(tmp_path / "goals"))
    goal = Goal(objective="atomic test")
    p.save(goal)

    # File should exist and be valid
    loaded = p.load(goal.id)
    assert loaded.objective == "atomic test"


def test_persistence_list_unfinished(tmp_path):
    p = GoalPersistence(str(tmp_path / "goals"))
    g1 = Goal(objective="pending goal", status=GoalStatus.PENDING)
    g2 = Goal(objective="completed goal", status=GoalStatus.COMPLETED)
    p.save(g1)
    p.save(g2)

    unfinished = p.list_unfinished()
    ids = [g.id for g in unfinished]
    assert g1.id in ids
    assert g2.id not in ids


def test_persistence_check_conflicts(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "test.txt").write_text("original", encoding="utf-8")

    p = GoalPersistence(str(tmp_path / "goals"))
    goal = Goal(
        objective="test",
        workspace=str(workspace),
        file_snapshot={"test.txt": "original"},
    )
    p.save(goal)

    # No conflict initially
    assert p.check_conflicts(goal.id) == []

    # Modify file
    (workspace / "test.txt").write_text("modified", encoding="utf-8")
    conflicts = p.check_conflicts(goal.id)
    assert len(conflicts) == 1
    assert "test.txt" in conflicts[0]
