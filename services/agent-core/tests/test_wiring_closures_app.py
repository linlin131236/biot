"""Wiring slice 3-closure (production entry): create_app wires the
TaskClosureService onto the ControlPlaneRepository when persistence_root is set.

Production wiring proof:
- With persistence_root configured, app.state closure service is repository-backed.
- A closure created through the service lands in the SQLite task_closures table.
- The legacy execution-audit.json closure_records are NOT written for closures.
"""

import json

from bolt_core.app import create_app
from bolt_core.task_closure import TaskTemplateId


def _make_app(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    return app, workspace, data_root


def test_app_closure_service_is_repository_backed(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    harness = app.state.harness
    service = harness.task_closure_service

    closure = service.start("wire me", TaskTemplateId.BUGFIX, run_id="run_1")

    db_path = data_root / "state" / "bolt.sqlite3"
    assert db_path.exists()
    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "select status from task_closures where id = ?", (closure.id,)
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row[0] == "pending"


def test_app_closure_not_written_to_legacy_json(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    service = app.state.harness.task_closure_service
    service.start("wire me", TaskTemplateId.BUGFIX)

    legacy = workspace / ".bolt" / "execution-audit.json"
    if legacy.exists():
        data = json.loads(legacy.read_text(encoding="utf-8"))
        assert data.get("closure_records", []) == []


def test_app_closure_recovers_after_app_rebuild(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    closure = app.state.harness.task_closure_service.start(
        "persist me", TaskTemplateId.BUGFIX, run_id="run_9"
    )
    del app

    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    recovered = rebuilt.state.harness.task_closure_service.load(closure.id)
    assert recovered is not None
    assert recovered.objective == "persist me"
    assert recovered.run_id == "run_9"


def test_app_queue_and_handoff_recover_from_repository_without_legacy_json(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    legacy = workspace / ".bolt" / "execution-audit.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        json.dumps({"version": 1, "queue_items": [], "handoff_records": [], "closure_records": []}),
        encoding="utf-8",
    )
    before = legacy.stat().st_mtime_ns
    closure = app.state.harness.task_closure_service.start("queue me", TaskTemplateId.BUGFIX)
    queue = app.state.execution_queue_service
    item = queue.create_item(closure.id, "manual_review", "Review", "Review", "read_only")
    queue.approve(item.id)
    record = app.state.execution_handoff_service.create_from_queue_item(item)

    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))

    assert rebuilt.state.execution_queue_service.get_item(item.id).status == "approved"
    assert rebuilt.state.execution_handoff_service.get_record(record.id).queue_item_id == item.id
    assert legacy.stat().st_mtime_ns == before
    assert json.loads(legacy.read_text(encoding="utf-8"))["queue_items"] == []
    assert json.loads(legacy.read_text(encoding="utf-8"))["handoff_records"] == []
