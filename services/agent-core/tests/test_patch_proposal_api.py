"""Integration tests for patch proposal API endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(project_dir=tmp_path)


@pytest.mark.anyio
async def test_create_patch_returns_validation(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/tools/patch/create", json={
            "description": "添加日志到 main.py",
            "files": [{
                "file_path": "src/main.py",
                "operation": "modify",
                "hunks": [{"old_start": 1, "old_count": 1, "new_start": 1, "new_count": 2, "lines": [" print('hello')", "+print('world')"]}],
            }],
            "unified_diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1,2 @@\n print('hello')\n+print('world')",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["valid"] is True
    assert data["validation"]["patch"] is not None
    assert data["validation"]["patch"]["total_files"] == 1
    assert "disclaimer" in data


@pytest.mark.anyio
async def test_list_patches_returns_empty_initially(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/tools/patch/list")

    assert resp.status_code == 200
    assert resp.json()["patches"] == []
    assert resp.json()["total"] == 0


@pytest.mark.anyio
async def test_preview_patch_returns_diff(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/tools/patch/create", json={
            "description": "添加日志",
            "files": [{"file_path": "src/main.py", "operation": "modify", "hunks": []}],
            "unified_diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1,2 @@\n print('hello')\n+print('world')",
        })
        patch_id = create.json()["validation"]["patch"]["patch_id"]
        resp = await client.get(f"/tools/patch/{patch_id}/preview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["patch_id"] == patch_id
    assert "unified_diff" in data
    assert data["total_files"] == 1
    assert "disclaimer" in data


@pytest.mark.anyio
async def test_preview_missing_patch_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/tools/patch/missing-id/preview")

    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


@pytest.mark.anyio
async def test_create_patch_blocks_dangerous_paths(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/tools/patch/create", json={
            "description": "修改 .claude 配置",
            "files": [{"file_path": ".claude/settings.json", "operation": "modify", "hunks": []}],
            "unified_diff": "--- a/.claude/settings.json\n+++ b/.claude/settings.json\n@@ -1 +1,2 @@\n {}\n+{}",
        })

    assert resp.status_code == 400
    data = resp.json()
    assert "拒绝" in str(data["detail"]) or "禁止" in str(data["detail"])
