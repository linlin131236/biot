import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_run_api_accepts_workspace_and_uses_it_for_tools(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("hello project", encoding="utf-8")
    async with _client() as client:
        run_response = await client.post("/harness/runs", json={"goal": "read", "workspace": str(workspace)})
        run_id = run_response.json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": str(target)}},
        )

    assert run_response.json()["workspace"] == str(workspace)
    assert tool_response.json()["status"] == "executed"
    assert "hello project" in (tool_response.json()["output"] or "")


@pytest.mark.anyio
async def test_run_api_workspace_isolation_denies_other_projects(tmp_path):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    outside_file = outside / "README.md"
    outside_file.write_text("outside", encoding="utf-8")
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read", "workspace": str(project)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": str(outside_file)}},
        )

    assert tool_response.json()["status"] == "denied"
    assert tool_response.json()["reason"] == "path outside workspace"


@pytest.mark.anyio
async def test_health_endpoint_reports_service_status():
    async with _client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "bolt-agent-core"}


@pytest.mark.anyio
async def test_p0_context_endpoint_returns_failure_shape():
    async with _client() as client:
        response = await client.get("/context/p0")

    assert response.status_code == 200
    assert response.json() == {"unresolved_failures": [], "hard_constraints": []}


@pytest.mark.anyio
async def test_harness_api_records_denied_tool_request():
    async with _client() as client:
        run_response = await client.post("/harness/runs", json={"goal": "safety check"})
        run_id = run_response.json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.run", "operation": "command", "payload": {"command": "rm -rf /"}},
        )
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")
        context_response = await client.get("/context/p0")

    assert tool_response.json()["status"] == "denied"
    assert "tool.requested" in [event["type"] for event in trace_response.json()]
    assert context_response.json()["unresolved_failures"][0]["tool"] == "shell.run"


@pytest.mark.anyio
async def test_memory_endpoints_expose_snapshot_and_p0_context():
    async with _client() as client:
        run_response = await client.post("/harness/runs", json={"goal": "memory check"})
        run_id = run_response.json()["id"]
        await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.run", "operation": "command", "payload": {"command": "rm -rf /"}},
        )
        memory_response = await client.get("/memory")
        p0_response = await client.get("/memory/p0")

    assert any(record["kind"] == "failure" for record in memory_response.json()["records"])
    assert p0_response.json()["unresolved_failures"][0]["tool"] == "shell.run"


@pytest.mark.anyio
async def test_permission_api_approves_pending_request_and_returns_execution(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "approve", "workspace": str(workspace)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": str(workspace)}},
        )
        request_id = tool_response.json()["request_id"]
        pending_response = await client.get("/permissions/pending")
        approve_response = await client.post(f"/permissions/{request_id}/approve")
        pending_after = await client.get("/permissions/pending")

    assert pending_response.json()[0]["request_id"] == request_id
    assert approve_response.json()["status"] == "executed"
    assert "Python" in approve_response.json()["output"]
    assert pending_after.json() == []


@pytest.mark.anyio
async def test_permission_api_records_failed_execution_in_memory(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "fail", "workspace": str(workspace)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": str(outside)}},
        )
        request_id = tool_response.json()["request_id"]
        approve_response = await client.post(f"/permissions/{request_id}/approve")
        p0_response = await client.get("/memory/p0")

    assert approve_response.json()["status"] == "failed"
    assert p0_response.json()["unresolved_failures"][0]["failure_class"] == "execution_failed"


@pytest.mark.anyio
async def test_permission_api_rejects_pending_request_without_execution(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "reject", "workspace": str(workspace)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": str(workspace)}},
        )
        request_id = tool_response.json()["request_id"]
        reject_response = await client.post(f"/permissions/{request_id}/reject")

    assert reject_response.json()["status"] == "rejected"


@pytest.mark.anyio
async def test_harness_api_executes_readonly_search_immediately():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "search"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "files.search", "operation": "search", "payload": {"query": "app.py"}},
        )
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")
        pending_response = await client.get("/permissions/pending")

    assert tool_response.json()["status"] == "executed"
    assert "app.py" in (tool_response.json()["output"] or "")
    assert pending_response.json() == []
    assert trace_response.json()[-1]["type"] == "tool.execution.completed"


@pytest.mark.anyio
async def test_harness_api_shell_execute_requires_approval_then_runs(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "shell", "workspace": str(workspace)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": str(workspace)}},
        )
        request_id = tool_response.json()["request_id"]
        pending_response = await client.get("/permissions/pending")
        approve_response = await client.post(f"/permissions/{request_id}/approve")
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    assert tool_response.json()["status"] == "pending_permission"
    assert pending_response.json()[0]["tool"] == "shell.execute"
    assert approve_response.json()["status"] == "executed"
    assert "Python" in (approve_response.json()["output"] or "")
    assert trace_response.json()[-1]["type"] == "tool.execution.completed"


@pytest.mark.anyio
async def test_memory_record_query_resolve_and_consolidate_endpoints():
    async with _client() as client:
        create_response = await client.post("/memory", json={"kind": "session", "scope": "run_1", "content": "I prefer Tauri"})
        memory_id = create_response.json()["id"]
        query_response = await client.get("/memory/records", params={"kind": "session", "query": "tauri"})
        consolidate_response = await client.post("/memory/consolidate")
        resolve_response = await client.post(f"/memory/{memory_id}/resolve")

    assert query_response.json()[0]["id"] == memory_id
    assert resolve_response.json()["status"] == "resolved"
    assert consolidate_response.json()["created"] >= 1


@pytest.mark.anyio
async def test_model_settings_endpoint_redacts_api_key():
    async with _client() as client:
        save_response = await client.post(
            "/model/settings",
            json={"provider": "openai-compatible", "base_url": "https://api.example", "api_key": "secret", "model": "test"},
        )
        status_response = await client.get("/model/settings")

    assert save_response.json()["has_api_key"] is True
    assert status_response.json()["model"] == "test"
    assert "secret" not in str(status_response.json())


@pytest.mark.anyio
async def test_agent_step_endpoint_records_llm_trace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Project\n", encoding="utf-8")
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read README", "workspace": str(workspace)})).json()["id"]
        step_response = await client.post(f"/harness/runs/{run_id}/agent-steps")
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    event_types = [event["type"] for event in trace_response.json()]
    assert step_response.json()["status"] == "executed"
    assert "tokens.recorded" in event_types
    assert "agent.step.completed" in event_types


@pytest.mark.anyio
async def test_harness_api_denies_reading_secret_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read secret", "workspace": str(workspace)})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": str(workspace / ".env")}},
        )
        p0_response = await client.get("/memory/p0")

    assert tool_response.json()["status"] == "denied"
    assert p0_response.json()["unresolved_failures"][0]["tool"] == "file.read"


@pytest.mark.anyio
async def test_agent_loop_endpoint_runs_bounded_loop():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "loop"})).json()["id"]
        response = await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 2})
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    assert response.json()["steps"] <= 2
    assert "agent.loop.started" in [event["type"] for event in trace_response.json()]


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_goals_unfinished_before_dynamic_route(tmp_path):
    """P1-1: /goals/unfinished must not be swallowed by /goals/{goal_id}."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "test", "workspace": str(workspace)})).json()["id"]
        # Create a goal first
        goal_resp = await client.post("/goals", json={
            "objective": "test goal", "criteria": ["done"],
            "max_steps": 5, "max_cost": 1.0, "max_wall_time": 60,
        })
        assert goal_resp.status_code == 200
        # Now request /goals/unfinished — must NOT 500
        unfinished_resp = await client.get("/goals/unfinished")
        assert unfinished_resp.status_code == 200
        assert isinstance(unfinished_resp.json(), list)


@pytest.mark.anyio
async def test_steering_endpoint_injects_into_run(tmp_path):
    """M39: POST /runs/{run_id}/steering injects a user steering message."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    async with _client() as client:
        run_resp = await client.post("/harness/runs", json={"goal": "steer test", "workspace": str(workspace)})
        run_id = run_resp.json()["id"]
        steer_resp = await client.post(f"/runs/{run_id}/steering", json={"content": "请先修测试"})
    assert steer_resp.status_code == 200
    assert steer_resp.json()["status"] == "injected"

