"""Task closure integration tests: API + harness + agent loop."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.harness import Harness
from bolt_core.model_gateway import ModelResponse, TokenUsage, ToolCall


@pytest.mark.anyio
async def test_run_loop_records_each_step_tool_result(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    app, run_id, _closure_id = await _app_run_and_closure(monkeypatch, str(workspace), _gateway("file.read", {"path": str(readme)}))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        loop_resp = await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 3})
        by_run_resp = await client.get(f"/task-closures/by-run/{run_id}")

    assert loop_resp.json()["steps"] == 3
    assert len(by_run_resp.json()["commands"]) == 3


@pytest.mark.anyio
async def test_run_loop_updates_closure_by_run(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    app, run_id, closure_id = await _app_run_and_closure(monkeypatch, str(workspace), _gateway("file.read", {"path": str(readme)}))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        loop_resp = await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 1})
        by_run_resp = await client.get(f"/task-closures/by-run/{run_id}")

    assert loop_resp.status_code == 200
    data = by_run_resp.json()
    assert data["id"] == closure_id
    assert data["status"] == "stopped"
    assert data["final_status"] == "stopped"
    assert data["commands"]


@pytest.mark.anyio
async def test_run_loop_records_pending_permission_without_approving(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("old\n", encoding="utf-8")
    app, run_id, _closure_id = await _app_run_and_closure(
        monkeypatch, str(workspace), _gateway("file.write", {"path": str(target), "proposed_content": "new\n"})
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        loop_resp = await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 3})
        closure_resp = await client.get(f"/task-closures/by-run/{run_id}")
        pending_resp = await client.get("/permissions/pending")

    assert loop_resp.json()["status"] == "pending_permission"
    closure = closure_resp.json()
    assert closure["status"] == "waiting_permission"
    assert closure["permission_request_ids"]
    assert pending_resp.json()[0]["status"] == "pending_permission"
    assert target.read_text(encoding="utf-8") == "old\n"


@pytest.mark.anyio
async def test_run_loop_without_closure_keeps_legacy_behavior(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    app = _patched_app(monkeypatch, str(workspace), _gateway("file.read", {"path": str(readme)}))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "read README", "workspace": str(workspace)})
        loop_resp = await client.post(f"/harness/runs/{run_resp.json()['id']}/agent-loops", json={"max_steps": 1})

    assert loop_resp.status_code == 200
    assert loop_resp.json()["status"] == "executed"


@pytest.mark.anyio
async def test_unknown_closure_bind_returns_404(tmp_path, monkeypatch):
    app = _patched_app(monkeypatch, str(tmp_path), _gateway("file.read", {"path": str(tmp_path / "README.md")}))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "read README", "workspace": str(tmp_path)})
        bind_resp = await client.post("/task-closures/missing/bind-run", json={"run_id": run_resp.json()["id"]})

    assert bind_resp.status_code == 404


@pytest.mark.anyio
async def test_unknown_run_bind_returns_404(tmp_path, monkeypatch):
    app = _patched_app(monkeypatch, str(tmp_path), _gateway("file.read", {"path": str(tmp_path / "README.md")}))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        closure_resp = await client.post("/task-closures", json={"objective": "读取 README", "template_id": "bugfix"})
        bind_resp = await client.post(f"/task-closures/{closure_resp.json()['id']}/bind-run", json={"run_id": "run_missing"})

    assert bind_resp.status_code == 404


@pytest.mark.anyio
async def test_closure_api_records_without_tool_execution(tmp_path, monkeypatch):
    app = _patched_app(monkeypatch, str(tmp_path), _gateway("file.read", {"path": str(tmp_path / "README.md")}))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        closure_resp = await client.post("/task-closures", json={"objective": "记录验证", "template_id": "quality"})
        closure_id = closure_resp.json()["id"]
        event_resp = await client.post(f"/task-closures/{closure_id}/events", json={"type": "command", "command": "pnpm test", "result": "通过"})
        pending_resp = await client.get("/permissions/pending")

    assert event_resp.status_code == 200
    assert event_resp.json()["commands"] == ["pnpm test"]
    assert pending_resp.json() == []


async def _app_run_and_closure(monkeypatch, workspace: str, gateway):
    app = _patched_app(monkeypatch, workspace, gateway)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "read README", "workspace": workspace})
        run_id = run_resp.json()["id"]
        closure_resp = await client.post("/task-closures", json={"objective": "读取 README", "template_id": "bugfix", "run_id": run_id})
        closure_id = closure_resp.json()["id"]
        bind_resp = await client.post(f"/task-closures/{closure_id}/bind-run", json={"run_id": run_id})
    assert bind_resp.status_code == 200
    return app, run_id, closure_id


def _patched_app(monkeypatch, workspace: str, gateway):
    original_init = Harness.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["workspace"] = workspace
        original_init(self, *args, **kwargs)
        self.agent_loop.gateway = gateway

    monkeypatch.setattr(Harness, "__init__", patched_init)
    return create_app()


def _gateway(tool: str, args: dict):
    call = ToolCall(f"call_{tool.replace('.', '_')}", tool, args)

    class Gateway:
        def complete(self, request):
            return ModelResponse("completed", None, TokenUsage(2, 3, 5), [call], None)

    return Gateway()
