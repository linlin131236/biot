"""Integration smoke for human approval execution queue."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_queue_approval_does_not_execute_or_complete_closure():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": "D:/Bolt/Bolt"})
        closure_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run_resp.json()["id"]})
        closure_id = closure_resp.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})

        assessment_resp = await client.get(f"/task-closures/{closure_id}/assessment")
        propose_resp = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item_id = propose_resp.json()[0]["id"]
        queue_resp = await client.get(f"/execution-queue?closure_id={closure_id}")
        approve_resp = await client.post(f"/execution-queue/{item_id}/approve")
        pending_resp = await client.get("/permissions/pending")
        closure_before = await client.get(f"/task-closures/{closure_id}")
        complete_resp = await client.post(f"/execution-queue/{item_id}/complete", json={"result": "用户已运行 pytest，12 passed"})
        closure_after_queue = await client.get(f"/task-closures/{closure_id}")
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "command", "command": "pytest", "result": "12 passed"})
        completed_resp = await client.post(f"/task-closures/{closure_id}/assessment")

    assert assessment_resp.json()["status"] == "missing_evidence"
    assert queue_resp.json()[0]["kind"] == "verification_command"
    assert queue_resp.json()[0]["status"] == "pending"
    assert approve_resp.json()["status"] == "approved"
    assert pending_resp.json() == []
    assert closure_before.json()["commands"] == []
    assert complete_resp.json()["status"] == "completed"
    assert closure_after_queue.json()["status"] != "completed"
    assert completed_resp.json()["status"] == "completed"
