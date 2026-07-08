from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.product_workbench import ProductWorkbenchService


def test_product_workbench_has_full_agent_flow():
    result = ProductWorkbenchService().snapshot()
    data = result.to_dict()

    assert data["read_only"] is True
    assert data["summary_cn"]
    assert data["current_stage_id"] == "user_intent"
    assert [stage["stage_id"] for stage in data["stages"]] == [
        "user_intent",
        "plan",
        "read_context",
        "patch_preview",
        "human_approval",
        "apply_patch",
        "run_tests",
        "audit_and_recovery",
    ]
    assert all(stage["label_cn"] for stage in data["stages"])


def test_product_workbench_safety_boundaries_are_explicit():
    data = ProductWorkbenchService().snapshot().to_dict()

    assert data["safety"]["auto_apply_allowed"] is False
    assert data["safety"]["auto_approve_allowed"] is False
    assert data["safety"]["human_approval_required"] is True
    assert data["safety"]["dangerous_operations_blocked"] is True
    assert "批准" in data["safety"]["summary_cn"]


def test_product_workbench_reports_patch_test_and_recovery_lanes():
    data = ProductWorkbenchService().snapshot().to_dict()

    lane_ids = [lane["lane_id"] for lane in data["lanes"]]
    assert lane_ids == ["patch", "test", "failure", "recovery"]
    assert all(lane["status"] in {"ready", "empty", "blocked"} for lane in data["lanes"])
    assert any("补丁" in lane["label_cn"] for lane in data["lanes"])
    assert any("测试" in lane["label_cn"] for lane in data["lanes"])
    assert any("恢复" in lane["label_cn"] for lane in data["lanes"])


def test_product_workbench_exposes_patch_approval_checklist():
    data = ProductWorkbenchService().snapshot().to_dict()

    checklist = data["patch_approval"]["checks"]
    assert data["patch_approval"]["label_cn"] == "补丁批准检查"
    assert [item["check_id"] for item in checklist] == [
        "preview_required",
        "target_scope_locked",
        "human_approval_required",
        "stale_recheck_required",
        "audit_required",
    ]
    assert all(item["required"] is True for item in checklist)
    assert all(item["label_cn"] for item in checklist)
    assert "自动批准" in data["patch_approval"]["warning_cn"]


def test_product_workbench_exposes_test_feedback_whitelist():
    data = ProductWorkbenchService().snapshot().to_dict()

    feedback = data["test_feedback"]
    assert feedback["label_cn"] == "白名单测试回填"
    assert feedback["arbitrary_shell_allowed"] is False
    assert [cmd["test_id"] for cmd in feedback["commands"]] == [
        "backend_unit",
        "backend_api",
        "shared_test",
        "desktop_test",
        "desktop_build",
        "quality_gate",
    ]
    assert all(cmd["label_cn"] for cmd in feedback["commands"])
    assert "任意 shell" in feedback["warning_cn"]


def test_product_workbench_api_is_registered():
    client = TestClient(create_app(project_dir="."))

    response = client.get("/product-workbench")

    assert response.status_code == 200
    data = response.json()
    assert data["read_only"] is True
    assert data["stages"][0]["label_cn"] == "用户意图"
