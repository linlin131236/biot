import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.harness import Harness


@pytest.fixture
def app():
    return create_app()


@pytest.mark.anyio
async def test_propose_then_get_queue_items(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        closure_id = await _missing_evidence_closure(client)

        propose_resp = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        queue_resp = await client.get(f"/execution-queue?closure_id={closure_id}")

    assert propose_resp.status_code == 200
    assert queue_resp.json()[0]["kind"] == "verification_command"
    assert queue_resp.json()[0]["status"] == "pending"


@pytest.mark.anyio
async def test_approve_only_changes_status(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)

        resp = await client.post(f"/execution-queue/{item['id']}/approve")

    assert resp.json()["status"] == "approved"
    assert resp.json()["result"] == ""


@pytest.mark.anyio
async def test_reject_records_reason(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)

        resp = await client.post(f"/execution-queue/{item['id']}/reject", json={"reason": "暂不处理"})

    assert resp.json()["status"] == "rejected"
    assert resp.json()["reason"] == "暂不处理"


@pytest.mark.anyio
async def test_complete_records_result(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)
        await client.post(f"/execution-queue/{item['id']}/approve")

        resp = await client.post(f"/execution-queue/{item['id']}/complete", json={"result": "用户已运行 pytest"})

    assert resp.json()["status"] == "completed"
    assert resp.json()["result"] == "用户已运行 pytest"


@pytest.mark.anyio
async def test_unknown_item_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/execution-queue/missing/approve")

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_repeated_approve_returns_409(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)
        await client.post(f"/execution-queue/{item['id']}/approve")

        resp = await client.post(f"/execution-queue/{item['id']}/approve")

    assert resp.status_code == 409


@pytest.mark.anyio
async def test_pending_fail_returns_409(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)

        resp = await client.post(f"/execution-queue/{item['id']}/fail", json={"result": "失败"})

    assert resp.status_code == 409


@pytest.mark.anyio
async def test_unknown_closure_propose_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/task-closures/missing/execution-queue/propose")

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_route_names_are_safe(app):
    for route in app.routes:
        path = getattr(route, "path", "")
        if "execution-queue" not in path:
            continue
        name = getattr(route, "name", "")
        assert "execute" not in name
        assert "shell" not in name
        assert "push" not in name
        assert "release" not in name
        assert "delete" not in name
        assert "approve_permission" not in name


@pytest.mark.anyio
async def test_queue_api_does_not_submit_tool_request(monkeypatch):
    calls = []
    original = Harness.submit_tool_request

    def spy(self, run_id, request):
        calls.append((run_id, request.tool))
        return original(self, run_id, request)

    monkeypatch.setattr(Harness, "submit_tool_request", spy)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        item = await _proposed_item(client)
        await client.post(f"/execution-queue/{item['id']}/approve")
        await client.post(f"/execution-queue/{item['id']}/complete", json={"result": "用户已运行"})

    assert calls == []


async def _missing_evidence_closure(client: AsyncClient) -> str:
    create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
    closure_id = create_resp.json()["id"]
    await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
    return closure_id


async def _proposed_item(client: AsyncClient) -> dict:
    closure_id = await _missing_evidence_closure(client)
    propose_resp = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
    return propose_resp.json()[0]
