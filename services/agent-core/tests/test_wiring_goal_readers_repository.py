"""Wiring slice 2b: goal readers (unfinished list, task_home, multi_task_queue)
read from the unified ControlPlaneRepository, not the legacy GoalService JSON.

Production wiring proof:
- /goals/unfinished lists goals from the repository tasks table.
- task_home cockpit and multi_task_queue surface goals sourced from the
  repository, not from the legacy in-memory/JSON GoalService.
- After the App/Harness is destroyed and rebuilt over the SAME persistence
  root, the unfinished goals are recovered from the repository.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


def _make_app(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    return app, workspace, data_root


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _goal_payload(workspace, objective="finish the reader slice"):
    return {
        "objective": objective,
        "criteria": ["listed from repo"],
        "max_steps": 5,
        "max_cost": 1.0,
        "max_wall_time": 60,
        "workspace": str(workspace),
    }


@pytest.mark.anyio
async def test_unfinished_goals_listed_from_repository(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        unfinished = (await client.get("/goals/unfinished")).json()

    assert gid in [g["id"] for g in unfinished]


@pytest.mark.anyio
async def test_unfinished_goals_recover_after_rebuild(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]

    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        unfinished = (await client.get("/goals/unfinished")).json()

    assert gid in [g["id"] for g in unfinished]


@pytest.mark.anyio
async def test_cleared_goal_absent_from_unfinished(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        await client.post(f"/goals/{gid}/clear")
        unfinished = (await client.get("/goals/unfinished")).json()

    assert gid not in [g["id"] for g in unfinished]


@pytest.mark.anyio
async def test_task_home_surfaces_repository_goal(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
        # rebuild to prove it is not reading the in-memory GoalService cache
    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        home = (await client.get("/task-home")).json()

    assert home.get("unfinished_goal_count", 0) >= 1
    assert home.get("current_goal", {}).get("id") == gid


@pytest.mark.anyio
async def test_multi_task_queue_surfaces_repository_goal(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        gid = (await client.post("/goals", json=_goal_payload(workspace))).json()["id"]
    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        queue = (await client.get("/multi-task-queue")).json()

    ids = [t.get("id") for t in queue.get("tasks", [])]
    assert gid in ids
