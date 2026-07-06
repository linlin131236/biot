import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.harness import Harness


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "execution-audit.json")


@pytest.mark.anyio
async def test_create_handoff_for_approved_verification_command(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)

        resp = await client.post(f"/execution-queue/{item['id']}/handoff")
        list_resp = await client.get(f"/execution-handoffs?closure_id={item['closure_id']}")
        pending_resp = await client.get("/permissions/pending")

    assert resp.status_code == 200
    assert resp.json()["handoff_type"] == "manual_verification"
    assert resp.json()["command"] == "pytest 或 pnpm test"
    assert list_resp.json()[0]["id"] == resp.json()["id"]
    assert pending_resp.json() == []


@pytest.mark.anyio
async def test_missing_item_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/execution-queue/missing/handoff")

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_unapproved_item_returns_409(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _pending_item(client)

        resp = await client.post(f"/execution-queue/{item['id']}/handoff")

    assert resp.status_code == 409


@pytest.mark.anyio
async def test_same_item_does_not_duplicate_handoff(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)

        first = await client.post(f"/execution-queue/{item['id']}/handoff")
        second = await client.post(f"/execution-queue/{item['id']}/handoff")

    assert first.json()["id"] == second.json()["id"]


@pytest.mark.anyio
async def test_complete_and_fail_only_update_handoff(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_item = await _approved_item(client)
        completed_handoff = await client.post(f"/execution-queue/{first_item['id']}/handoff")
        second_item = await _approved_item(client)
        failed_handoff = await client.post(f"/execution-queue/{second_item['id']}/handoff")

        completed = await client.post(f"/execution-handoffs/{completed_handoff.json()['id']}/complete", json={"result": "用户已完成"})
        failed = await client.post(f"/execution-handoffs/{failed_handoff.json()['id']}/fail", json={"result": "用户标记失败"})

    assert completed.json()["status"] == "completed"
    assert failed.json()["status"] == "failed"
    assert failed.json()["result"] == "用户标记失败"


@pytest.mark.anyio
async def test_terminal_handoff_transitions_return_409(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_item = await _approved_item(client)
        completed_handoff = await client.post(f"/execution-queue/{first_item['id']}/handoff")
        await client.post(f"/execution-handoffs/{completed_handoff.json()['id']}/complete", json={"result": "用户已完成"})
        fail_completed = await client.post(f"/execution-handoffs/{completed_handoff.json()['id']}/fail", json={"result": "用户标记失败"})

        second_item = await _approved_item(client)
        failed_handoff = await client.post(f"/execution-queue/{second_item['id']}/handoff")
        await client.post(f"/execution-handoffs/{failed_handoff.json()['id']}/fail", json={"result": "用户标记失败"})
        complete_failed = await client.post(f"/execution-handoffs/{failed_handoff.json()['id']}/complete", json={"result": "用户已完成"})

    assert fail_completed.status_code == 409
    assert complete_failed.status_code == 409


@pytest.mark.anyio
async def test_handoff_api_does_not_execute_or_approve(monkeypatch, tmp_path):
    calls: list[str] = []

    def submit_spy(self, run_id, request):
        calls.append("submit_tool_request")
        raise AssertionError("submit_tool_request must not be called")

    def approve_spy(self, request_id):
        calls.append("approve_permission")
        raise AssertionError("approve_permission must not be called")

    def loop_spy(self, run_id, max_steps=3):
        calls.append("run_agent_loop")
        raise AssertionError("run_agent_loop must not be called")

    monkeypatch.setattr(Harness, "submit_tool_request", submit_spy)
    monkeypatch.setattr(Harness, "approve_permission", approve_spy)
    monkeypatch.setattr(Harness, "run_agent_loop", loop_spy)
    app = create_app(tmp_path / "execution-audit.json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)
        await client.post(f"/execution-queue/{item['id']}/handoff")

    assert calls == []


@pytest.mark.anyio
async def test_api_handoff_restores_after_app_rebuild(tmp_path):
    audit_path = tmp_path / "execution-audit.json"
    first_app = create_app(audit_path)
    first_transport = ASGITransport(app=first_app)
    async with AsyncClient(transport=first_transport, base_url="http://test") as client:
        item = await _approved_item(client)
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        other_item = await _approved_item(client)
        await client.post(f"/execution-queue/{other_item['id']}/handoff")
        await client.post(f"/execution-handoffs/{handoff.json()['id']}/complete", json={"result": "用户已完成"})

    second_app = create_app(audit_path)
    second_transport = ASGITransport(app=second_app)
    async with AsyncClient(transport=second_transport, base_url="http://test") as client:
        list_resp = await client.get(f"/execution-handoffs?closure_id={item['closure_id']}")
        fail_completed = await client.post(f"/execution-handoffs/{handoff.json()['id']}/fail", json={"result": "用户标记失败"})

    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"] == handoff.json()["id"]
    assert list_resp.json()[0]["status"] == "completed"
    assert fail_completed.status_code == 409


@pytest.mark.anyio
async def test_request_permission_creates_pending_permission(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")

        resp = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        pending_resp = await client.get("/permissions/pending")

    assert resp.status_code == 200
    assert resp.json()["status"] == "waiting_permission"
    assert resp.json()["permission_status"] == "pending_permission"
    assert resp.json()["permission_request_id"] == pending_resp.json()[0]["request_id"]
    assert pending_resp.json()[0]["tool"] == "shell.execute"


@pytest.mark.anyio
async def test_request_permission_unknown_handoff_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/execution-handoffs/missing/request-permission")

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_request_permission_rejects_goal_input(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "planning"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "executing"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "stopped"})
        queue_resp = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        goal_input = next(item for item in queue_resp.json() if item["kind"] == "replan")
        approved = await client.post(f"/execution-queue/{goal_input['id']}/approve")
        handoff = await client.post(f"/execution-queue/{approved.json()['id']}/handoff")

        resp = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")

    assert resp.status_code == 409


@pytest.mark.anyio
async def test_request_permission_does_not_duplicate_pending_permission(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")

        first = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        second = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        pending_resp = await client.get("/permissions/pending")

    assert second.json()["permission_request_id"] == first.json()["permission_request_id"]
    assert len(pending_resp.json()) == 1


@pytest.mark.anyio
async def test_request_permission_does_not_execute_or_approve(monkeypatch, tmp_path):
    calls: list[str] = []

    def submit_spy(self, run_id, request):
        calls.append("submit_tool_request")
        raise AssertionError("submit_tool_request must not be called")

    def approve_spy(self, request_id):
        calls.append("approve_permission")
        raise AssertionError("approve_permission must not be called")

    def loop_spy(self, run_id, max_steps=3):
        calls.append("run_agent_loop")
        raise AssertionError("run_agent_loop must not be called")

    monkeypatch.setattr(Harness, "submit_tool_request", submit_spy)
    monkeypatch.setattr(Harness, "approve_permission", approve_spy)
    monkeypatch.setattr(Harness, "run_agent_loop", loop_spy)
    app = create_app(tmp_path / "execution-audit.json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _approved_item(client)
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")

    assert calls == []


async def _pending_item(client: AsyncClient) -> dict:
    create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
    closure_id = create_resp.json()["id"]
    await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
    propose_resp = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
    return propose_resp.json()[0]


async def _approved_item(client: AsyncClient) -> dict:
    item = await _pending_item(client)
    approved = await client.post(f"/execution-queue/{item['id']}/approve")
    return approved.json()
