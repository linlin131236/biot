from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.product_workbench_dogfood import ProductWorkbenchDogfoodService


def test_product_workbench_dogfood_all_checks_pass():
    result = ProductWorkbenchDogfoodService().run()
    data = result.to_dict()

    assert data["total"] >= 10
    assert data["failed"] == 0
    assert data["ready_for_review"] is True
    assert "M126-M129" in data["summary_cn"]


def test_product_workbench_dogfood_checks_core_lanes():
    data = ProductWorkbenchDogfoodService().run().to_dict()
    ids = [check["check_id"] for check in data["checks"]]

    assert "workbench_api_registered" in ids
    assert "desktop_panel_registered" in ids
    assert "patch_approval_visible" in ids
    assert "test_feedback_visible" in ids
    assert "failure_recovery_visible" in ids
    assert "no_auto_actions" in ids


def test_product_workbench_dogfood_api_registered():
    client = TestClient(create_app(project_dir="."))

    response = client.get("/product-workbench-dogfood")

    assert response.status_code == 200
    assert response.json()["ready_for_review"] is True
