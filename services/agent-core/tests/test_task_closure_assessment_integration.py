"""Integration smoke for evidence-based task closure assessment."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.harness import Harness
from bolt_core.model_gateway import ModelResponse, TokenUsage, ToolCall


@pytest.mark.anyio
async def test_assessment_completes_when_recorded_evidence_is_sufficient(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = _patched_app(monkeypatch, str(workspace), _gateway("file.read", {"path": str(workspace / "README.md")}))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(workspace)})
        closure_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run_resp.json()["id"]})
        closure_id = closure_resp.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "command", "command": "pytest", "result": "12 passed"})
        get_assessment = await client.get(f"/task-closures/{closure_id}/assessment")
        post_assessment = await client.post(f"/task-closures/{closure_id}/assessment")

    assert get_assessment.json()["status"] == "passed"
    assert post_assessment.json()["status"] == "completed"


@pytest.mark.anyio
async def test_pending_permission_assessment_stays_waiting_permission(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("old\n", encoding="utf-8")
    app, run_id, closure_id = await _app_run_and_closure(
        monkeypatch, str(workspace), _gateway("file.write", {"path": str(target), "proposed_content": "new\n"}), "bugfix"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 3})
        get_assessment = await client.get(f"/task-closures/{closure_id}/assessment")
        post_assessment = await client.post(f"/task-closures/{closure_id}/assessment")

    assert get_assessment.json()["status"] == "waiting_permission"
    assert post_assessment.json()["status"] == "waiting_permission"
    assert target.read_text(encoding="utf-8") == "old\n"


@pytest.mark.anyio
async def test_max_steps_with_missing_evidence_does_not_complete(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    app, run_id, closure_id = await _app_run_and_closure(monkeypatch, str(workspace), _gateway("file.read", {"path": str(readme)}), "bugfix")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(f"/harness/runs/{run_id}/agent-loops", json={"max_steps": 1})
        get_assessment = await client.get(f"/task-closures/{closure_id}/assessment")
        post_assessment = await client.post(f"/task-closures/{closure_id}/assessment")

    assert get_assessment.json()["status"] == "stopped"
    assert post_assessment.json()["status"] == "stopped"


async def _app_run_and_closure(monkeypatch, workspace: str, gateway, template_id: str):
    app = _patched_app(monkeypatch, workspace, gateway)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.post("/harness/runs", json={"goal": "read README", "workspace": workspace})
        run_id = run_resp.json()["id"]
        closure_resp = await client.post("/task-closures", json={"objective": "读取 README", "template_id": template_id, "run_id": run_id})
        closure_id = closure_resp.json()["id"]
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
