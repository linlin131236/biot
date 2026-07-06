import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_request_permission_uses_bound_run_workspace(tmp_path):
    workspace = tmp_path / "user-workspace"
    workspace.mkdir()
    app = create_app(tmp_path / "execution-audit.json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(workspace)})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        await client.post(f"/task-closures/{closure.json()['id']}/events", json={"type": "file_change", "path": "src/app.py"})
        item = (await client.post(f"/task-closures/{closure.json()['id']}/execution-queue/propose")).json()[0]
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        pending = await client.get("/permissions/pending")

    assert pending.json()[0]["run_id"] == run.json()["id"]
    assert pending.json()[0]["payload"]["workdir"] == str(workspace)
