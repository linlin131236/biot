import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_autonomy_integration_smoke_connects_core_routes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "main.txt"
    target.write_text("hello\n", encoding="utf-8")

    async with _client() as client:
        run = (await client.post("/harness/runs", json={"goal": "integration smoke", "workspace": str(workspace)})).json()
        goal = (await client.post("/goals", json={
            "objective": "finish integration smoke",
            "criteria": ["read file", "approve patch", "review gate evaluated"],
            "max_steps": 5,
            "max_cost": 1.0,
            "max_wall_time": 60,
            "workspace": str(workspace),
        })).json()
        conversation = (await client.post("/conversations", json={"system_prompt": "stay scoped"})).json()
        add_message = await client.post(
            f"/conversations/{conversation['id']}/messages",
            json={"role": "user", "content": "run smoke"},
        )
        read_result = (await client.post(
            f"/harness/runs/{run['id']}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": str(target)}},
        )).json()
        patch_result = (await client.post(
            f"/harness/runs/{run['id']}/tool-requests",
            json={
                "tool": "file.patch",
                "operation": "patch",
                "payload": {"path": str(target), "old_string": "hello", "new_string": "hello bolt"},
            },
        )).json()
        approved = (await client.post(f"/permissions/{patch_result['request_id']}/approve")).json()
        checkpoint = (await client.post("/checkpoints", json={
            "run_id": run["id"],
            "goal_id": goal["id"],
            "changed_files": ["main.txt"],
            "constraints": ["do not add new agent capability"],
            "pending_permissions": [],
            "evidence_refs": [patch_result["request_id"]],
        })).json()
        loaded_checkpoint = (await client.get(f"/checkpoints/{checkpoint['id']}")).json()
        review = (await client.post("/review/evaluate", json={
            "items": ["pytest", "desktop build"],
            "results": {"pytest": True, "desktop build": False},
        })).json()
        loop = (await client.post(f"/harness/runs/{run['id']}/agent-loops", json={"max_steps": 1})).json()
        timeline = (await client.get(f"/runs/{run['id']}/timeline")).json()

    assert add_message.status_code == 200
    assert read_result["status"] == "executed"
    assert patch_result["status"] == "pending_permission"
    assert approved["status"] == "executed"
    assert target.read_text(encoding="utf-8") == "hello bolt\n"
    assert loaded_checkpoint["file_contents"]["main.txt"] == "hello bolt\n"
    assert loaded_checkpoint["constraints"] == ["do not add new agent capability"]
    assert review == {"passed": False, "failures": ["desktop build"]}
    assert loop["steps"] <= 1
    assert any(event["type"] == "agent.loop.started" for event in timeline)


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")
