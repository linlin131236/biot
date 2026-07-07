import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_health_endpoint_reports_degraded_audit_store(tmp_path):
    audit_path = tmp_path / "execution-audit.json"
    audit_path.write_text("{broken", encoding="utf-8")
    transport = ASGITransport(app=create_app(execution_audit_path=audit_path))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["audit_store"] == "degraded"
    assert "execution audit JSON is damaged" in response.json()["audit_error"]
