import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_checkpoint_restore_api_requires_confirmation(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("before\n", encoding="utf-8")
    app = create_app(project_dir=tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cp = (await client.post("/checkpoints", json={
            "run_id": "run_1",
            "goal_id": "goal_1",
            "changed_files": ["app.py"],
        })).json()
        target.write_text("after\n", encoding="utf-8")
        response = await client.post(
            f"/checkpoints/{cp['id']}/restore",
            json={"confirm_restore": False},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "恢复检查点需要用户明确确认"
    assert target.read_text(encoding="utf-8") == "after\n"


@pytest.mark.anyio
async def test_checkpoint_restore_api_restores_saved_files(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("before\n", encoding="utf-8")
    app = create_app(project_dir=tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cp = (await client.post("/checkpoints", json={
            "run_id": "run_1",
            "goal_id": "goal_1",
            "changed_files": ["app.py"],
        })).json()
        target.write_text("after\n", encoding="utf-8")
        response = await client.post(
            f"/checkpoints/{cp['id']}/restore",
            json={"confirm_restore": True},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "restored"
    assert response.json()["restored_files"] == ["app.py"]
    assert target.read_text(encoding="utf-8") == "before\n"
