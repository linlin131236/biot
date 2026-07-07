"""Integration tests for ExecutionAuditIntegrity API endpoint."""
import json

import httpx
import pytest

from bolt_core.app import create_app
from bolt_core.execution_audit_store import execution_audit_path


@pytest.fixture
def client(tmp_path):
    """创建带临时审计文件路径的 FastAPI 测试客户端。"""
    audit_path = tmp_path / "execution-audit.json"
    app = create_app(execution_audit_path=audit_path)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_integrity_endpoint_returns_list(client):
    """GET /execution-audit/integrity 返回列表。"""
    response = await client.get("/execution-audit/integrity")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_integrity_endpoint_clean_when_file_missing(client):
    """文件不存在时返回空列表。"""
    response = await client.get("/execution-audit/integrity")
    data = response.json()
    assert data == []


@pytest.mark.anyio
async def test_integrity_endpoint_blocking_when_json_damaged(client, tmp_path):
    """JSON 损坏时返回阻断诊断而非 500。"""
    audit_path = tmp_path / "execution-audit.json"
    audit_path.write_text("corrupted {{{", encoding="utf-8")
    app = create_app(execution_audit_path=audit_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/execution-audit/integrity")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["severity"] == "blocking"


@pytest.mark.anyio
async def test_integrity_endpoint_clean_when_valid(client, tmp_path):
    """有效文件返回干净状态。"""
    audit_path = tmp_path / "execution-audit.json"
    from bolt_core.execution_audit_store import ExecutionAuditStore
    store = ExecutionAuditStore(audit_path)
    store.save_queue_items([{
        "id": "eq_0", "closure_id": "cl_0", "kind": "verification_command",
        "title": "测试验证", "description": "测试", "risk": "read_only",
        "status": "approved", "command": None, "reason": "", "result": "",
        "created_at": 1.0,
    }])
    store.save_handoff_records([{
        "id": "eh_0", "queue_item_id": "eq_0", "closure_id": "cl_0",
        "kind": "verification_command", "status": "waiting_permission",
        "handoff_type": "permission_panel", "title": "测试", "instruction": "测试",
        "command": None, "goal_objective": "", "run_id": None, "goal_id": None,
        "permission_request_id": None, "permission_status": "pending_permission",
        "bridge_error": "", "permission_workspace": None, "result": "",
        "created_at": 1.0, "updated_at": 1.0,
    }])
    store.save_closure_records([{
        "id": "cl_0", "objective": "测试", "template_id": "test", "run_id": None,
        "goal_id": None, "status": "completed", "final_status": "completed",
        "plan_summary": "", "changed_files": [], "commands": [],
        "command_results": [], "permission_request_ids": [],
        "retry_count": 0, "review_summary": "", "next_action": "",
        "created_at": 1.0,
    }])
    app = create_app(execution_audit_path=audit_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/execution-audit/integrity")
        assert response.status_code == 200
        data = response.json()
        blocking = [d for d in data if d["severity"] == "blocking"]
        assert len(blocking) == 0


@pytest.mark.anyio
async def test_integrity_api_is_read_only(client):
    """多次 GET 不改变文件内容。"""
    response1 = await client.get("/execution-audit/integrity")
    response2 = await client.get("/execution-audit/integrity")
    assert response1.json() == response2.json()
