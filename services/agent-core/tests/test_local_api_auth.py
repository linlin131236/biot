from fastapi import FastAPI
from fastapi.testclient import TestClient

from bolt_core.app import create_app
import bolt_core.app as app_module
from bolt_core.local_api_auth import install_local_api_auth


def test_desktop_production_auth_exposes_only_health_publicly(tmp_path):
    app = create_app(
        execution_audit_path=tmp_path / "audit.json",
        project_dir=tmp_path,
        local_api_token="secret-token",
        require_local_api_token=True,
        desktop_production=True,
    )
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 401
    assert client.options("/memory").status_code == 401


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


def test_create_app_without_token_remains_available_for_unit_tests(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/memory")

    assert response.status_code == 200


def test_strict_local_auth_requires_token():
    try:
        install_local_api_auth(FastAPI(), None, require_token=True)
    except RuntimeError as exc:
        assert "鉴权令牌未配置" in str(exc)
    else:
        raise AssertionError("strict local auth must reject missing token")


def test_module_app_without_env_token_fails_on_startup():
    client = TestClient(app_module.app)
    try:
        with client:
            pass
    except RuntimeError as exc:
        assert "鉴权令牌未配置" in str(exc)
    else:
        raise AssertionError("module-level app must fail closed without token")
