import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


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
async def test_permission_api_approves_pending_request_and_returns_execution():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "approve"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.run", "operation": "command", "payload": {"command": "pnpm test"}},
        )
        request_id = tool_response.json()["request_id"]
        pending_response = await client.get("/permissions/pending")
        approve_response = await client.post(f"/permissions/{request_id}/approve")
        pending_after = await client.get("/permissions/pending")

    assert pending_response.json()[0]["request_id"] == request_id
    assert approve_response.json()["status"] == "executed"
    assert approve_response.json()["output"] == "fake execution completed"
    assert pending_after.json() == []


@pytest.mark.anyio
async def test_permission_api_records_failed_execution_in_memory():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "fail"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.run", "operation": "command", "payload": {"command": "pnpm test", "fail": True}},
        )
        request_id = tool_response.json()["request_id"]
        approve_response = await client.post(f"/permissions/{request_id}/approve")
        p0_response = await client.get("/memory/p0")

    assert approve_response.json()["status"] == "failed"
    assert p0_response.json()["unresolved_failures"][0]["failure_class"] == "execution_failed"


@pytest.mark.anyio
async def test_permission_api_rejects_pending_request_without_execution():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "reject"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.run", "operation": "command", "payload": {"command": "pnpm test"}},
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
async def test_harness_api_shell_execute_requires_approval_then_runs():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "shell"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": "D:/Bolt/Bolt"}},
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
async def test_agent_step_endpoint_records_llm_trace():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read README"})).json()["id"]
        step_response = await client.post(f"/harness/runs/{run_id}/agent-steps")
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    event_types = [event["type"] for event in trace_response.json()]
    assert step_response.json()["status"] == "executed"
    assert "tokens.recorded" in event_types
    assert "agent.step.completed" in event_types


@pytest.mark.anyio
async def test_harness_api_denies_reading_secret_file():
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read secret"})).json()["id"]
        tool_response = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": "D:/Bolt/Bolt/.env"}},
        )
        p0_response = await client.get("/memory/p0")

    assert tool_response.json()["status"] == "denied"
    assert p0_response.json()["unresolved_failures"][0]["tool"] == "file.read"


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")
