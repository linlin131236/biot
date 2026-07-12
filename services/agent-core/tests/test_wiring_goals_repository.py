"""Wiring slice 2a: /goals CRUD state persists through the unified
ControlPlaneRepository (tasks table), not the legacy GoalService JSON files.

Production wiring proof:
- A goal created through the HTTP endpoint lands in the SQLite tasks table.
- Goal status transitions (pause/resume/clear) update the task row.
- After the App/Harness is destroyed and rebuilt over the SAME persistence
  root, the goal state is recovered from the repository.
- The legacy .bolt/goals/*.json must NOT be the production write path anymore.
- A rejected (too-vague) goal is not written to the tasks table.
- Secret objectives are rejected without writing a canary.
"""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _make_app(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    return app, workspace, data_root


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _goal_payload(workspace, objective="finish the wiring slice"):
    return {
        "objective": objective,
        "criteria": ["tests green", "no dual write"],
        "constraints": ["surgical change only"],
        "max_steps": 5,
        "max_cost": 1.0,
        "max_wall_time": 60,
        "workspace": str(workspace),
    }


@pytest.mark.anyio
async def test_goal_persists_into_repository_tasks(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        goal = (await client.post("/goals", json=_goal_payload(workspace))).json()
        gid = goal["id"]
        assert goal["status"] == "pending"

    db_path = data_root / "state" / "bolt.sqlite3"
    assert db_path.exists()
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "select status from tasks where id = ?", (gid,)
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row[0] == "pending"


@pytest.mark.anyio
async def test_goal_status_transitions_update_repository(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        paused = (await client.post(f"/goals/{gid}/pause")).json()
        assert paused["status"] == "paused"
        resumed = (await client.post(f"/goals/{gid}/resume")).json()
        assert resumed["status"] == "running"

    db_path = data_root / "state" / "bolt.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "select status from tasks where id = ?", (gid,)
        ).fetchone()
    finally:
        connection.close()
    assert row[0] == "running"


@pytest.mark.anyio
async def test_goal_state_recovers_after_app_rebuild(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        await client.post(f"/goals/{gid}/pause")

    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        goal = (await client.get(f"/goals/{gid}")).json()

    assert goal["id"] == gid
    assert goal["status"] == "paused"
    assert goal["objective"] == "finish the wiring slice"
    assert goal["criteria"] == ["tests green", "no dual write"]


@pytest.mark.anyio
async def test_clear_goal_marks_terminal_in_repository(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        cleared = (await client.post(f"/goals/{gid}/clear")).json()
        assert cleared["status"] == "stopped"

    db_path = data_root / "state" / "bolt.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "select status from tasks where id = ?", (gid,)
        ).fetchone()
    finally:
        connection.close()
    assert row[0] == "stopped"


@pytest.mark.anyio
async def test_legacy_goal_json_not_written_in_production(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        await client.post("/goals", json=_goal_payload(workspace))

    goals_dir = workspace / ".bolt" / "goals"
    written = list(goals_dir.glob("goal_*.json")) if goals_dir.exists() else []
    assert written == []


@pytest.mark.anyio
async def test_rejected_goal_is_not_written_to_repository(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        goal = (await client.post("/goals", json=_goal_payload(workspace, "do stuff"))).json()
        assert goal["status"] == "rejected"

    db_path = data_root / "state" / "bolt.sqlite3"
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        try:
            count = connection.execute("select count(*) from tasks").fetchone()[0]
        finally:
            connection.close()
        assert count == 0


@pytest.mark.anyio
async def test_goal_objective_with_secret_is_rejected_without_canary(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        resp = await client.post(
            "/goals",
            json=_goal_payload(workspace, f"use key ghp_{_SECRET_CANARY}{'A' * 20}"),
        )
        assert resp.status_code == 422

    db_path = data_root / "state" / "bolt.sqlite3"
    if db_path.exists():
        assert _SECRET_CANARY.encode() not in db_path.read_bytes()
