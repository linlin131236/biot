"""Tests for TaskHomeService — aggregate task home summary."""
import pytest
from datetime import datetime, timezone

from bolt_core.task_home import TaskHomeService, TaskHomeSummary


class FakeGoal:
    def __init__(self, data: dict):
        self._data = data

    def to_dict(self):
        return self._data


class FakeGoalService:
    def __init__(self, goals=None):
        raw = goals or []
        self._goals = [FakeGoal(g) if isinstance(g, dict) else g for g in raw]

    def unfinished_goals(self):
        return self._goals

    def get_goal(self, goal_id: str):
        for g in self._goals:
            if g.to_dict().get("id") == goal_id:
                return g
        return None


class FakeHarness:
    def __init__(self, goal_service=None, permissions=None):
        self.goal_service = goal_service or FakeGoalService()
        self.permissions = permissions or FakePermissions()


class FakePermissions:
    def __init__(self, pending=None):
        self._pending = pending or []

    def pending_permissions(self):
        return self._pending


class FakeDiagnostics:
    def __init__(self, diagnostics=None):
        self._diagnostics = diagnostics or []

    def list_diagnostics(self):
        return self._diagnostics


class FakePlanner:
    def __init__(self, graphs=None):
        self._graphs = graphs or []

    def list_graphs(self):
        return self._graphs


def make_goal(goal_id="g1", objective="测试目标", status="running"):
    return {"id": goal_id, "objective": objective, "status": status,
            "criteria": [], "max_steps": 10, "max_cost": 100, "max_wall_time": 3600,
            "workspace": "/tmp", "step_count": 3}


def make_diag(code="D001", severity="blocking", summary="测试阻断"):
    sev_label = {"blocking": "阻断", "warning": "警告", "info": "提示"}.get(severity, severity)
    return {
        "code": code, "severity": severity, "severity_label": sev_label,
        "summary": summary, "suggestion": "建议动作",
    }


# ── Basic summary ───────────────────────────────────────────────────────

def test_summary_empty_state():
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert result.unfinished_goal_count == 0
    assert result.pending_permission_count == 0
    assert result.blocker_count == 0
    assert result.warning_count == 0
    assert result.active_task_count == 0
    assert result.current_goal is None
    assert isinstance(result.next_suggestions, list)
    assert isinstance(result.recent_events, list)


def test_summary_with_unfinished_goals():
    goals = FakeGoalService([make_goal("g1", "任务A", "running"), make_goal("g2", "任务B", "paused")])
    svc = TaskHomeService(FakeHarness(goals), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert result.unfinished_goal_count == 2


def test_summary_with_pending_permissions():
    perms = FakePermissions([type("P", (), {"id": "p1"})(), type("P", (), {"id": "p2"})()])
    svc = TaskHomeService(FakeHarness(permissions=perms), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert result.pending_permission_count == 2


def test_summary_with_diagnostics():
    diags = FakeDiagnostics([
        make_diag("D001", "blocking"),
        make_diag("D002", "blocking"),
        make_diag("D003", "warning"),
        make_diag("D004", "info"),
    ])
    svc = TaskHomeService(FakeHarness(), diags, FakePlanner())
    result = svc.get_summary()
    assert result.blocker_count == 2
    assert result.warning_count == 1


def test_summary_with_active_tasks():
    planner = FakePlanner([
        type("G", (), {"to_dict": lambda: {"id": "pg1", "title": "图1"}})(),
        type("G", (), {"to_dict": lambda: {"id": "pg2", "title": "图2"}})(),
    ])
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), planner)
    result = svc.get_summary()
    assert result.active_task_count == 2


def test_summary_with_current_goal():
    goals = FakeGoalService([
        make_goal("g1", "当前任务", "running"),
        make_goal("g2", "另一个任务", "paused"),
    ])
    svc = TaskHomeService(FakeHarness(goals), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert result.current_goal is not None
    assert result.current_goal["id"] == "g1"
    assert result.current_goal["objective"] == "当前任务"


# ── Suggestions ─────────────────────────────────────────────────────────

def test_suggestions_when_blockers_exist():
    diags = FakeDiagnostics([make_diag("D001", "blocking", "关键阻断")])
    svc = TaskHomeService(FakeHarness(), diags, FakePlanner())
    result = svc.get_summary()
    assert any("阻断" in s for s in result.next_suggestions)


def test_suggestions_when_permissions_pending():
    perms = FakePermissions([type("P", (), {"id": "p1"})()])
    svc = TaskHomeService(FakeHarness(permissions=perms), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert any("权限" in s for s in result.next_suggestions)


def test_suggestions_when_idle():
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert any("目标" in s for s in result.next_suggestions)


# ── to_dict ─────────────────────────────────────────────────────────────

def test_summary_to_dict():
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    d = result.to_dict()
    assert "current_goal" in d
    assert "unfinished_goal_count" in d
    assert "pending_permission_count" in d
    assert "blocker_count" in d
    assert "warning_count" in d
    assert "active_task_count" in d
    assert "next_suggestions" in d
    assert "recent_events" in d
    assert "updated_at" in d
    assert isinstance(d["next_suggestions"], list)
    assert all(isinstance(s, str) for s in d["next_suggestions"])


# ── Edge cases ──────────────────────────────────────────────────────────

def test_summary_handles_service_errors_gracefully():
    """When a service raises, summary should still return with partial data."""

    class BrokenDiagnostics:
        def list_diagnostics(self):
            raise RuntimeError("模拟服务故障")

    svc = TaskHomeService(FakeHarness(), BrokenDiagnostics(), FakePlanner())
    result = svc.get_summary()
    # Should still return a valid summary
    assert result.blocker_count == 0
    assert result.unfinished_goal_count == 0


def test_summary_recent_events_empty():
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    assert result.recent_events == []


def test_chinese_labels():
    svc = TaskHomeService(FakeHarness(), FakeDiagnostics(), FakePlanner())
    result = svc.get_summary()
    d = result.to_dict()
    # Verify Chinese suggestions
    for s in d["next_suggestions"]:
        # Each suggestion should contain at least some Chinese characters
        assert any('\u4e00' <= c <= '\u9fff' for c in s)
