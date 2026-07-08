"""Targeted tests for M152 workspace API and desktop_settings extensions."""
import json
import os
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.desktop_settings import DesktopSettingsService, DEFAULT_SETTINGS
from bolt_core.goal import Goal, GoalStatus


def _write_goal(goals_dir: Path, goal: Goal) -> None:
    goals_dir.mkdir(parents=True, exist_ok=True)
    path = goals_dir / f"{goal.id}.json"
    path.write_text(json.dumps(goal.to_dict(), indent=2), encoding="utf-8")


# --- desktop_settings extensions ---

def test_default_settings_has_empty_recent_workspaces():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)
        status = service.get_status()
        assert status["recent_workspaces"] == []


def test_add_recent_workspace_dedup_and_limit():
    with tempfile.TemporaryDirectory() as tmp:
        service = DesktopSettingsService(tmp)
        service.add_recent_workspace("/tmp/ws_a")
        service.add_recent_workspace("/tmp/ws_b")
        service.add_recent_workspace("/tmp/ws_a")  # dedup + reorder to front

        status = service.get_status()
        # After re-adding ws_a, it should be at the front
        assert status["recent_workspaces"] == ["/tmp/ws_a", "/tmp/ws_b"]

        # Fill beyond limit
        for i in range(15):
            service.add_recent_workspace(f"/tmp/ws_{i}")
        assert len(status["recent_workspaces"]) <= 10


# --- workspace API via ASGI client ---

@pytest.fixture
def app(tmp_path):
    # Create a .bolt/goals dir with test data
    goals_dir = tmp_path / ".bolt" / "goals"
    goals_dir.mkdir(parents=True, exist_ok=True)
    _write_goal(goals_dir, Goal(objective="修复登录 bug", status=GoalStatus.RUNNING, workspace=str(tmp_path)))
    _write_goal(goals_dir, Goal(objective="更新文档", status=GoalStatus.PENDING, workspace=str(tmp_path)))
    # Add a corrupt file that should be skipped
    (goals_dir / "goal_corrupt.json").write_text("NOT VALID JSON{{{")
    return create_app(project_dir=str(tmp_path))


@pytest.mark.anyio
async def test_workspace_status_accessible(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/workspace/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accessible"] is True
        assert isinstance(data["path"], str)
        assert len(data["path"]) > 0


@pytest.mark.anyio
async def test_workspace_recent_sessions_returns_goals(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/workspace/recent-sessions")
        assert resp.status_code == 200
        data = resp.json()
        sessions = data["sessions"]
        assert len(sessions) == 2
        titles = [s["title"] for s in sessions]
        assert "修复登录 bug" in titles
        assert "更新文档" in titles
        for s in sessions:
            assert s["status"] in ("running", "pending")
            assert "id" in s


@pytest.mark.anyio
async def test_workspace_recent_sessions_respects_limit(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/workspace/recent-sessions?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) <= 1


@pytest.mark.anyio
async def test_workspace_recent_sessions_skips_corrupt_files(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/workspace/recent-sessions")
        assert resp.status_code == 200
        data = resp.json()
        sessions = data["sessions"]
        # Only 2 valid goals, corrupt file should be skipped
        assert len(sessions) == 2
