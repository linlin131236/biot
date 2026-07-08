import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_permission_center_uses_existing_permission_gate_approval(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(project_dir=workspace)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = (await client.post(
            "/harness/runs",
            json={"goal": "shell", "workspace": str(workspace)},
        )).json()["id"]
        request = await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={
                "tool": "shell.execute",
                "operation": "command",
                "payload": {"command": "python --version", "workdir": str(workspace)},
            },
        )
        request_id = request.json()["request_id"]
        before = await client.get("/permission-center")
        approved = await client.post(f"/permissions/{request_id}/approve")
        after = await client.get("/permission-center")

    assert before.json()["total_pending"] == 1
    assert before.json()["items"][0]["id"] == f"perm_{request_id}"
    assert before.json()["items"][0]["request_id"] == request_id
    assert approved.json()["status"] == "executed"
    assert after.json()["total_pending"] == 0
