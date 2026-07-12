"""Task 4 acceptance coverage for repository-backed runtime recovery."""

import httpx
import pytest

from bolt_core.app import create_app
from bolt_core.model_gateway import ModelResponse, TokenUsage, ToolCall
from bolt_core.task_closure import TaskTemplateId
from bolt_core.tool_protocol import ToolRequest


def test_app_rebuild_recovers_runtime_and_execution_records_without_legacy_writes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    legacy_files = {
        workspace / ".bolt" / "conversations.db": b"legacy-conversations",
        workspace / ".bolt" / "goals" / "goal_legacy.json": b'{"id":"legacy"}',
        workspace / ".bolt" / "execution-audit.json": b'{"version":1,"queue_items":[],"handoff_records":[]}',
    }
    for path, content in legacy_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in legacy_files}
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("rebuild runtime")
    closure = app.state.harness.task_closure_service.start(
        "rebuild closure", TaskTemplateId.BUGFIX, run_id=run.id
    )
    queue = app.state.execution_queue_service.create_item(
        closure.id, "manual_review", "Review", "Review", "read_only"
    )
    handoff = app.state.execution_handoff_service.create_from_queue_item(queue)
    goal = app.state.harness.goals.create_goal({"objective": "rebuild checkpoint"})
    checkpoint = app.state.checkpoint_service.create(run.id, goal.id)
    events = app.state.harness.trace(run.id)

    del app
    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)

    assert run.id in rebuilt.state.harness.runs
    assert [event.type for event in rebuilt.state.harness.trace(run.id)] == [
        event.type for event in events
    ]
    assert rebuilt.state.harness.task_closure_service.load(closure.id) is not None
    assert rebuilt.state.execution_queue_service.get_item(queue.id).status == "pending"
    assert rebuilt.state.execution_handoff_service.get_record(handoff.id).id == handoff.id
    assert rebuilt.state.checkpoint_service.load(checkpoint.id) is not None
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in legacy_files
    } == before


def test_runtime_secret_is_absent_from_sqlite_wal_shm_and_backups(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("safe runtime")
    canary = b"C4N4RY7D83CBB5XX"

    with pytest.raises(ValueError):
        app.state.persistence.append_runtime_event(
            "event_secret", run.id, 3, "status", {"apiKey": canary.decode()}
        )
    app.state.persistence.database.create_backup("after-runtime-secret")

    database = app.state.persistence.database.path
    candidates = [
        database,
        database.with_name(f"{database.name}-wal"),
        database.with_name(f"{database.name}-shm"),
        *sorted((database.parent / "backups").glob("*.sqlite3")),
    ]
    assert all(canary not in path.read_bytes() for path in candidates if path.exists())


def test_completed_persistent_loop_closes_runtime_task_and_session(tmp_path):
    class CompletedGateway:
        def complete(self, _request):
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(
        project_dir=workspace,
        persistence_root=tmp_path / "user-data",
        model_gateway=CompletedGateway(),
    )
    run = app.state.harness.create_run("complete runtime")

    result = app.state.harness.run_agent_loop(run.id)

    assert result.status == "completed"
    assert app.state.persistence.load_task(f"task_{run.id}")["status"] == "completed"
    session = next(
        item for item in app.state.persistence.list_runtime_sessions(
            app.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert session["status"] == "completed"


def test_completed_persistent_agent_step_closes_runtime_task_and_session(tmp_path):
    class CompletedGateway:
        def complete(self, _request):
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(
        project_dir=workspace,
        persistence_root=tmp_path / "user-data",
        model_gateway=CompletedGateway(),
    )
    run = app.state.harness.create_run("complete runtime step")

    result = app.state.harness.run_agent_step(run.id)

    assert result.status == "completed"
    assert app.state.persistence.load_task(f"task_{run.id}")["status"] == "completed"
    session = next(
        item for item in app.state.persistence.list_runtime_sessions(
            app.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert session["status"] == "completed"


@pytest.mark.anyio
async def test_rebuilt_terminal_runtime_rejects_agent_steps_with_conflict(tmp_path):
    class CompletedGateway:
        def complete(self, _request):
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=CompletedGateway(),
    )
    run = app.state.harness.create_run("complete then rebuild")
    assert app.state.harness.run_agent_step(run.id).status == "completed"

    rebuilt = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=CompletedGateway(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=rebuilt, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        timeline = await client.get(f"/runs/{run.id}/timeline")
        rejected = await client.post(f"/harness/runs/{run.id}/agent-steps")

    assert timeline.status_code == 200
    assert rejected.status_code == 409


def test_app_rebuild_does_not_recover_a_running_goal_as_runtime_work(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    goal = app.state.harness.goals.create_goal({"objective": "finish recovery coverage"})
    app.state.harness.goals.pause_goal(goal.id)
    app.state.harness.goals.resume_goal(goal.id)

    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)

    assert rebuilt.state.harness.goals.get_goal(goal.id).status.value == "running"


def test_persistent_loop_waiting_for_approval_keeps_runtime_open(tmp_path):
    class WriteGateway:
        def complete(self, _request):
            return ModelResponse(
                "completed", None, TokenUsage(1, 1, 2),
                [ToolCall("call_write", "file.write", {
                    "path": "README.md", "proposed_content": "updated\n",
                })], None,
            )

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("original\n", encoding="utf-8")
    app = create_app(
        project_dir=workspace,
        persistence_root=tmp_path / "user-data",
        model_gateway=WriteGateway(),
    )
    run = app.state.harness.create_run("request approval")

    result = app.state.harness.run_agent_loop(run.id)

    assert result.status == "pending_permission"
    assert app.state.persistence.load_task(f"task_{run.id}")["status"] == "waiting_approval"
    session = next(
        item for item in app.state.persistence.list_runtime_sessions(
            app.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    assert session["status"] == "waiting_approval"
    approval = app.state.harness.pending_permissions()[0]
    assert app.state.harness.approve_permission(approval.request_id).status == "executed"


def test_persistent_pending_approval_recovers_for_human_resolution(tmp_path):
    class WriteGateway:
        def complete(self, _request):
            return ModelResponse(
                "completed", None, TokenUsage(1, 1, 2),
                [ToolCall("call_write", "file.write", {
                    "path": "README.md", "proposed_content": "updated\n",
                })], None,
            )

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("original\n", encoding="utf-8")
    data_root = tmp_path / "user-data"
    app = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=WriteGateway(),
    )
    run = app.state.harness.create_run("recover approval")
    assert app.state.harness.run_agent_loop(run.id).status == "pending_permission"

    rebuilt = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=WriteGateway(),
    )

    pending = rebuilt.state.harness.pending_permissions()
    assert [item.run_id for item in pending] == [run.id]
    assert rebuilt.state.harness.approve_permission(pending[0].request_id).status == "executed"


def test_multiple_pending_approvals_survive_rebuild(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "first.txt").write_text("one\n", encoding="utf-8")
    (workspace / "second.txt").write_text("two\n", encoding="utf-8")
    data_root = tmp_path / "user-data"
    app = create_app(project_dir=workspace, persistence_root=data_root)
    run = app.state.harness.create_run("recover multiple approvals")
    for path, content in (("first.txt", "ONE\n"), ("second.txt", "TWO\n")):
        result = app.state.harness.submit_tool_request(
            run.id, ToolRequest.create(
                "file.write", "write", {"path": path, "proposed_content": content},
            ),
        )
        assert result.status == "pending_permission"

    rebuilt = create_app(project_dir=workspace, persistence_root=data_root)

    pending = rebuilt.state.harness.pending_permissions()
    assert len(pending) == 2
    assert {item.payload["change_set"]["path"] for item in pending} == {
        "first.txt", "second.txt",
    }


@pytest.mark.anyio
async def test_app_rebuild_reconciles_terminal_task_with_open_runtime_session(tmp_path):
    class CompletedGateway:
        def complete(self, _request):
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data_root = tmp_path / "user-data"
    app = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=CompletedGateway(),
    )
    run = app.state.harness.create_run("reconcile terminal runtime")
    task = app.state.persistence.load_task(f"task_{run.id}")
    app.state.persistence.update_task(
        task["id"], task["revision"], "completed", task["payload"],
    )

    rebuilt = create_app(
        project_dir=workspace, persistence_root=data_root, model_gateway=CompletedGateway(),
    )
    session = next(
        item for item in rebuilt.state.persistence.list_runtime_sessions(
            rebuilt.state.harness._workspace_id
        ) if item["id"] == run.id
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=rebuilt, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        rejected = await client.post(f"/harness/runs/{run.id}/agent-steps")

    assert session["status"] == "completed"
    assert rejected.status_code == 409
