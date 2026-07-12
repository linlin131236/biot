"""Production Harness runtime events use the control-plane repository."""

import json
import sqlite3

import httpx
import pytest

from bolt_core.app import create_app
from bolt_core.task_closure import TaskTemplateId


@pytest.mark.anyio
async def test_persistence_app_rebuild_restores_runtime_trace_without_legacy_db(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/harness/runs", json={"goal": "trace", "workspace": str(workspace)})
        run_id = response.json()["id"]
        events = (await client.get(f"/runs/{run_id}/timeline")).json()
    assert events and events[0]["type"] == "run.created"
    assert not (workspace / ".bolt" / "conversations.db").exists()

    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)
    assert run_id in rebuilt.state.harness.runs
    assert [event.type for event in rebuilt.state.harness.trace(run_id)] == [
        event["type"] for event in events
    ]

    connection = sqlite3.connect(data_root / "state" / "bolt.sqlite3")
    try:
        assert connection.execute(
            "select count(*) from runtime_events where runtime_session_id = ?", (run_id,)
        ).fetchone()[0] == len(events)
    finally:
        connection.close()


@pytest.mark.anyio
async def test_persistence_goal_can_bind_closure_through_repository(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(project_dir=workspace, persistence_root=tmp_path / "user-data")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        goal = (await client.post("/goals", json={"objective": "repo goal"})).json()
        response = await client.post(
            "/task-closures",
            json={"objective": "repo goal", "template_id": "bugfix", "goal_id": goal["id"]},
        )
    assert response.status_code == 200
    assert response.json()["goal_id"] == goal["id"]


def test_blocked_persistent_loop_closes_runtime_task_and_session(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("requires a configured model")

    result = app.state.harness.run_agent_loop(run.id)

    assert result.status == "failed"
    task = app.state.persistence.load_task(f"task_{run.id}")
    session = next(
        item for item in app.state.persistence.list_runtime_sessions(
            app.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert task["status"] == "failed"
    assert session["status"] == "failed"


def test_credential_blocked_persistent_loop_closes_runtime_task_and_session(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    app.state.harness.update_model_settings({
        "revision": 0,
        "credential_id": "wincred.v1.absent",
    })
    run = app.state.harness.create_run("requires a configured model")

    result = app.state.harness.run_agent_loop(run.id)

    assert result.status == "failed"
    task = app.state.persistence.load_task(f"task_{run.id}")
    session = next(
        item for item in app.state.persistence.list_runtime_sessions(
            app.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert task["status"] == "failed"
    assert session["status"] == "failed"
