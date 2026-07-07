"""API tests for M121 crash recovery readiness."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_crash_recovery_endpoint_returns_readonly_result(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/reliability/crash-recovery")

    assert response.status_code == 200
    data = response.json()
    assert "review" in data
    assert "只读" in data["disclaimer"]
