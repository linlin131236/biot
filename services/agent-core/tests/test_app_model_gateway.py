import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_agent_step_endpoint_records_llm_trace_with_explicit_fake(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Project\n", encoding="utf-8")
    async with _client() as client:
        await client.post("/model/settings", json={"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})
        run_id = (await client.post("/harness/runs", json={"goal": "read README", "workspace": str(workspace)})).json()["id"]
        step_response = await client.post(f"/harness/runs/{run_id}/agent-steps")
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    event_types = [event["type"] for event in trace_response.json()]
    assert step_response.json()["status"] == "executed"
    assert "tokens.recorded" in event_types
    assert "agent.step.completed" in event_types


@pytest.mark.anyio
async def test_agent_step_endpoint_fails_closed_without_model_key(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with _client() as client:
        run_id = (await client.post("/harness/runs", json={"goal": "read README", "workspace": str(workspace)})).json()["id"]
        step_response = await client.post(f"/harness/runs/{run_id}/agent-steps")
        trace_response = await client.get(f"/harness/runs/{run_id}/trace")

    event_types = [event["type"] for event in trace_response.json()]
    assert step_response.json()["status"] == "failed"
    assert step_response.json()["error"] == "api key missing"
    assert "tool.execution.started" not in event_types


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")
