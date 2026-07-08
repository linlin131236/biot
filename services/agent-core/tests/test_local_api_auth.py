from fastapi.testclient import TestClient

from bolt_core.app import create_app


def test_health_remains_public_when_local_token_is_required(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=tmp_path, local_api_token="secret-token")
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_api_rejects_missing_local_token(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=tmp_path, local_api_token="secret-token")
    client = TestClient(app)

    response = client.get("/memory")

    assert response.status_code == 401
    assert response.json()["detail"] == "缺少或无效的本地访问令牌"


def test_protected_api_accepts_bearer_local_token(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=tmp_path, local_api_token="secret-token")
    client = TestClient(app)

    response = client.get("/memory", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert "records" in response.json()
