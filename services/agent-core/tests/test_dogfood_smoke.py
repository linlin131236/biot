"""
M32 Desktop Dogfood Smoke — backend integration test for the full dogfood path.

This test verifies the backend supports the real product path that a desktop
user would follow: run → goal → conversation → file.read → file.patch →
approve → checkpoint → review → timeline.

Unlike the M31 integration smoke which only tests route connectivity,
this test focuses on dogfood-specific concerns:
- Runtime startup validation
- Permission gate enforcement (write ops must require approval)
- Checkpoint round-trip preserves constraints
- Review gate correctly identifies failures
- Timeline includes all expected event types
- Unwired surfaces return proper errors (not fake data)
"""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_dogfood_smoke_full_product_path(tmp_path, monkeypatch):
    """Verify the complete dogfood product path through the Agent Core API."""
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "main.txt"
    target.write_text("hello\n", encoding="utf-8")

    async with _client() as client:
        # 1. Create a harness run with workspace
        run_resp = await client.post(
            "/harness/runs",
            json={"goal": "dogfood smoke", "workspace": str(workspace)},
        )
        assert run_resp.status_code == 200
        run = run_resp.json()
        run_id = run["id"]
        assert run["workspace"] == str(workspace)

        # 2. Create a goal
        goal_resp = await client.post("/goals", json={
            "objective": "complete dogfood smoke",
            "criteria": ["file read", "patch approved", "checkpoint loaded"],
            "max_steps": 5,
            "max_cost": 1.0,
            "max_wall_time": 60,
            "workspace": str(workspace),
        })
        assert goal_resp.status_code == 200
        goal = goal_resp.json()
        goal_id = goal["id"]
        assert goal["status"] == "pending"

        # 3. Create conversation and add message
        conv_resp = await client.post("/conversations", json={"system_prompt": "stay scoped"})
        assert conv_resp.status_code == 200
        conv_id = conv_resp.json()["id"]

        msg_resp = await client.post(
            f"/conversations/{conv_id}/messages",
            json={"role": "user", "content": "run dogfood smoke"},
        )
        assert msg_resp.status_code == 200

        # 4. file.read — executed immediately, no permission needed
        read_result = (await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={"tool": "file.read", "operation": "read", "payload": {"path": str(target)}},
        )).json()
        assert read_result["status"] == "executed"
        assert "hello" in read_result["output"]

        # 5. file.patch → must be pending_permission (write requires approval)
        patch_result = (await client.post(
            f"/harness/runs/{run_id}/tool-requests",
            json={
                "tool": "file.patch",
                "operation": "patch",
                "payload": {"path": str(target), "old_string": "hello", "new_string": "hello bolt"},
            },
        )).json()
        assert patch_result["status"] == "pending_permission", (
            f"file.patch must require permission, got: {patch_result['status']}"
        )
        request_id = patch_result["request_id"]

        # 6. Approve permission → file actually changes
        approved = (await client.post(f"/permissions/{request_id}/approve")).json()
        assert approved["status"] == "executed"
        assert target.read_text(encoding="utf-8") == "hello bolt\n"

        # 7. Create and load checkpoint
        checkpoint = (await client.post("/checkpoints", json={
            "run_id": run_id,
            "goal_id": goal_id,
            "changed_files": ["main.txt"],
            "constraints": ["do not add new agent capability"],
            "pending_permissions": [],
            "evidence_refs": [request_id],
        })).json()
        cp_id = checkpoint["id"]
        assert checkpoint["file_contents"]["main.txt"] == "hello bolt\n"
        assert checkpoint["constraints"] == ["do not add new agent capability"]

        loaded = (await client.get(f"/checkpoints/{cp_id}")).json()
        assert loaded["file_contents"]["main.txt"] == "hello bolt\n"
        assert loaded["constraints"] == ["do not add new agent capability"]

        # 8. Review evaluate — intentional failure
        review = (await client.post("/review/evaluate", json={
            "items": ["pytest", "desktop build"],
            "results": {"pytest": True, "desktop build": False},
        })).json()
        assert review["passed"] is False
        assert review["failures"] == ["desktop build"]

        # 9. Fetch run timeline — must include events
        timeline = (await client.get(f"/runs/{run_id}/timeline")).json()
        assert len(timeline) > 0
        event_types = [e["type"] for e in timeline]
        assert "run.created" in event_types

        # 10. Verify health endpoint works
        health = (await client.get("/health")).json()
        assert health["status"] == "ok"


@pytest.mark.anyio
async def test_dogfood_smoke_reject_permission_does_not_modify_file(tmp_path, monkeypatch):
    """Verify rejecting a file.patch permission does NOT modify the file."""
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "protected.txt"
    target.write_text("original\n", encoding="utf-8")

    async with _client() as client:
        run = (await client.post("/harness/runs", json={"goal": "reject test", "workspace": str(workspace)})).json()
        patch_result = (await client.post(
            f"/harness/runs/{run['id']}/tool-requests",
            json={
                "tool": "file.patch",
                "operation": "patch",
                "payload": {"path": str(target), "old_string": "original", "new_string": "modified"},
            },
        )).json()
        assert patch_result["status"] == "pending_permission"

        rejected = (await client.post(f"/permissions/{patch_result['request_id']}/reject")).json()
        assert rejected["status"] == "rejected"
        assert target.read_text(encoding="utf-8") == "original\n"


@pytest.mark.anyio
async def test_dogfood_smoke_unwired_surface_returns_404(tmp_path, monkeypatch):
    """Verify that unwired surfaces return proper HTTP errors, not fake data."""
    monkeypatch.chdir(tmp_path)

    async with _client() as client:
        # /skills does not exist — must return 404, not fake data
        resp = await client.get("/skills")
        assert resp.status_code == 404

        # /delegation/tasks does not exist
        resp = await client.get("/delegation/tasks")
        assert resp.status_code == 404


def _client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    return AsyncClient(transport=transport, base_url="http://test")
