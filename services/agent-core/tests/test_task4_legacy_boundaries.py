"""Task 4 proves production persistence does not read legacy truth sources."""

from fastapi.testclient import TestClient

from bolt_core.app import create_app


def test_persistence_workspace_sessions_do_not_read_legacy_goal_json(tmp_path):
    workspace = tmp_path / "workspace"
    legacy = workspace / ".bolt" / "goals"
    legacy.mkdir(parents=True)
    (legacy / "goal_legacy.json").write_text(
        '{"id":"goal_legacy","objective":"legacy","status":"running"}',
        encoding="utf-8",
    )
    app = create_app(project_dir=workspace, persistence_root=tmp_path / "user-data")
    with TestClient(app) as client:
        sessions = client.get("/workspace/recent-sessions")
    assert sessions.status_code == 200
    assert sessions.json()["sessions"] == []


def test_persistence_release_diagnostics_do_not_read_legacy_execution_audit(tmp_path):
    workspace = tmp_path / "workspace"
    legacy = workspace / ".bolt" / "execution-audit.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("not-json", encoding="utf-8")
    app = create_app(project_dir=workspace, persistence_root=tmp_path / "user-data")
    with TestClient(app) as client:
        integrity = client.get("/execution-audit/integrity")
    assert integrity.status_code == 200
    assert all(item.get("code") != "json_damaged" for item in integrity.json())


def test_startup_closes_runtime_session_left_open_after_terminal_task_write(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("reconcile runtime")
    with app.state.persistence.database.transaction() as connection:
        connection.execute(
            "update tasks set status = 'completed' where id = ?", (f"task_{run.id}",)
        )

    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)
    session = next(
        item for item in rebuilt.state.persistence.list_runtime_sessions(
            rebuilt.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert session["status"] == "completed"
