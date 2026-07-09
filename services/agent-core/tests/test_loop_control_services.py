from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.auto_continue_service import AutoContinueService
from bolt_core.auto_fix_service import AutoFixService
from bolt_core.autonomous_loop_service import AutonomousLoopService
from bolt_core.gate_freeze_service import GateFreezeService
from bolt_core.tool_verification_service import ToolVerificationService


def test_gate_freeze_state_is_shared_across_instances():
    first = GateFreezeService()
    second = GateFreezeService()
    first.unfreeze()
    first.freeze("发布冻结")
    assert second.is_frozen() is True
    assert second.get_status()["reason"] == "发布冻结"
    second.unfreeze()


def test_tool_verification_is_read_only_and_healthy():
    result = ToolVerificationService().verify_all()
    assert result["overall"] == "healthy"
    assert result["healthy"] == result["total"]
    assert all("tool_id" in tool for tool in result["tools"])


def test_auto_continue_caps_rounds_at_five():
    result = AutoContinueService().set_auto_continue(True, 99)
    assert result["enabled"] is True
    assert result["max_rounds"] == 5


def test_auto_fix_keeps_p1_findings_for_human_review():
    result = AutoFixService().auto_fix(
        [
            {"severity": "P1", "description": "权限绕过"},
            {"severity": "P2", "description": "trailing whitespace"},
        ],
        "a = 1   \n",
    )
    assert result["fixed"] == 1
    assert result["remaining"] == 1
    assert result["proposed_code"] == "a = 1"


def test_autonomous_loop_is_bounded_and_diagnostic_only():
    result = AutonomousLoopService().run_loop("修复测试", "D:/Bolt/Bolt", 50)
    assert result["max_rounds"] == 5
    assert result["status"] == "completed"
    assert result["trace"][0]["role"] == "planner"


def test_gate_freeze_blocks_auto_continue_and_autonomous_loop(tmp_path):
    app = create_app(project_dir=tmp_path)
    client = TestClient(app)
    client.post("/gate/unfreeze")

    freeze = client.post("/gate/freeze", json={"reason": "复审冻结"})
    assert freeze.status_code == 200
    assert freeze.json()["frozen"] is True

    auto_continue = client.post("/orchestrator/auto-continue", json={"enabled": True})
    assert auto_continue.status_code == 423
    assert "Gate 已冻结" in auto_continue.json()["detail"]

    loop = client.post("/orchestrator/autonomous-loop", json={"task_description": "继续", "workspace": "D:/Bolt/Bolt"})
    assert loop.status_code == 423
    assert "Gate 已冻结" in loop.json()["detail"]

    client.post("/gate/unfreeze")
    ok = client.post("/orchestrator/auto-continue", json={"enabled": True, "max_rounds": 3})
    assert ok.status_code == 200
    assert ok.json()["max_rounds"] == 3


def test_gate_freeze_blocks_legacy_permission_approval(tmp_path):
    client = TestClient(create_app(project_dir=tmp_path))
    client.post("/gate/unfreeze")
    run = client.post("/harness/runs", json={"goal": "冻结批准测试", "workspace": str(tmp_path)}).json()["id"]
    proposed = client.post(
        f"/harness/runs/{run}/tool-requests",
        json={
            "tool": "file.write",
            "operation": "write",
            "payload": {"path": str(tmp_path / "blocked.txt"), "proposed_content": "blocked\n"},
        },
    )
    assert proposed.status_code == 200
    request_id = proposed.json()["request_id"]

    client.post("/gate/freeze", json={"reason": "冻结批准"})
    approved = client.post(f"/permissions/{request_id}/approve")
    assert approved.status_code == 423
    assert "Gate 已冻结" in approved.json()["detail"]
    assert not (tmp_path / "blocked.txt").exists()
    client.post("/gate/unfreeze")


def test_auto_continue_rejects_invalid_rounds(tmp_path):
    client = TestClient(create_app(project_dir=tmp_path))
    client.post("/gate/unfreeze")
    response = client.post("/orchestrator/auto-continue", json={"enabled": True, "max_rounds": "abc"})
    assert response.status_code == 400
    assert "max_rounds 必须是数字" in response.json()["detail"]


def test_autonomous_loop_rejects_invalid_rounds(tmp_path):
    client = TestClient(create_app(project_dir=tmp_path))
    client.post("/gate/unfreeze")
    response = client.post(
        "/orchestrator/autonomous-loop",
        json={"task_description": "继续", "workspace": str(tmp_path), "max_rounds": "abc"},
    )
    assert response.status_code == 400
    assert "max_rounds 必须是数字" in response.json()["detail"]


def test_app_registers_tool_verification_route(tmp_path):
    client = TestClient(create_app(project_dir=tmp_path))
    response = client.get("/tools/verify")
    assert response.status_code == 200
    assert response.json()["overall"] == "healthy"
