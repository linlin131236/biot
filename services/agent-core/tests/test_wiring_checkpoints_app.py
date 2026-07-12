import sqlite3

from fastapi.testclient import TestClient

from bolt_core.app import create_app


def test_persistent_app_checkpoints_use_repository_and_recover(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("checkpoint goal")
    goal = app.state.harness.goals.create_goal({"objective": "checkpoint goal"})

    with TestClient(app) as client:
        response = client.post(
            "/checkpoints",
            json={"run_id": run.id, "goal_id": goal.id, "changed_files": []},
        )
        assert response.status_code == 200
        checkpoint_id = response.json()["id"]

    database = data_root / "state" / "bolt.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "select task_id, task_revision from checkpoints where id = ?",
            (checkpoint_id,),
        ).fetchone()
    assert row == (goal.id, 0)
    assert not list((workspace / ".bolt" / "checkpoints").glob("*.json"))

    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)
    with TestClient(rebuilt) as client:
        loaded = client.get(f"/checkpoints/{checkpoint_id}")
    assert loaded.status_code == 200
    assert loaded.json()["id"] == checkpoint_id
