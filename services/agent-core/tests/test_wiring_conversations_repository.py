"""Wiring slice 1: /conversations endpoints persist through the unified
ControlPlaneRepository (sessions/messages), not the legacy ConversationStore.

Production wiring proof:
- Messages written through the HTTP endpoints must land in the SQLite
  control-plane database under persistence_root.
- After the App/Harness is destroyed and rebuilt over the SAME persistence
  root, the conversation history must be recovered from the repository.
- The legacy .bolt/conversations.db must NOT be the production write path
  anymore (no new rows written there when persistence is configured).
- Secret metadata must be rejected without writing a canary.
"""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _make_app(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    data_root = tmp_path / "user-data"
    app = create_app(
        project_dir=str(workspace),
        persistence_root=str(data_root),
    )
    return app, workspace, data_root


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_conversation_message_persists_into_repository_sqlite(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        conv = (await client.post("/conversations", json={"system_prompt": "stay scoped"})).json()
        cid = conv["id"]
        resp = await client.post(
            f"/conversations/{cid}/messages",
            json={"role": "user", "content": "hello repository"},
        )
        assert resp.status_code == 200

    # The message must be in the control-plane SQLite database.
    db_path = data_root / "state" / "bolt.sqlite3"
    assert db_path.exists()
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "select content from messages where session_id = ? order by sequence",
            (cid,),
        ).fetchall()
    finally:
        connection.close()
    assert [r[0] for r in rows] == ["stay scoped", "hello repository"]


@pytest.mark.anyio
async def test_conversation_history_recovers_after_app_rebuild(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        conv = (await client.post("/conversations", json={"system_prompt": "sys"})).json()
        cid = conv["id"]
        await client.post(
            f"/conversations/{cid}/messages",
            json={"role": "user", "content": "first"},
        )
        await client.post(
            f"/conversations/{cid}/messages",
            json={"role": "assistant", "content": "second"},
        )

    # Destroy the app/harness entirely, rebuild over the SAME data_root.
    del app
    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        history = (await client.get(f"/conversations/{cid}")).json()

    assert [m["role"] for m in history] == ["system", "user", "assistant"]
    assert [m["content"] for m in history] == ["sys", "first", "second"]


@pytest.mark.anyio
async def test_conversations_listed_from_repository_after_rebuild(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        conv = (await client.post("/conversations", json={"system_prompt": "sys"})).json()
        cid = conv["id"]

    rebuilt = create_app(project_dir=str(workspace), persistence_root=str(data_root))
    async with _client(rebuilt) as client:
        listed = (await client.get("/conversations")).json()

    assert cid in listed


@pytest.mark.anyio
async def test_legacy_conversations_db_not_written_in_production(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        conv = (await client.post("/conversations", json={"system_prompt": "sys"})).json()
        await client.post(
            f"/conversations/{conv['id']}/messages",
            json={"role": "user", "content": "hello"},
        )

    # The legacy store file must not become a production write path.
    legacy = workspace / ".bolt" / "conversations.db"
    if legacy.exists():
        connection = sqlite3.connect(legacy)
        try:
            count = connection.execute("select count(*) from messages").fetchone()[0]
        finally:
            connection.close()
        assert count == 0


@pytest.mark.anyio
async def test_conversation_message_rejects_secret_metadata_without_canary(tmp_path):
    app, workspace, data_root = _make_app(tmp_path)
    async with _client(app) as client:
        conv = (await client.post("/conversations", json={"system_prompt": "sys"})).json()
        resp = await client.post(
            f"/conversations/{conv['id']}/messages",
            json={"role": "user", "content": "hi", "metadata": {"apiKey": _SECRET_CANARY}},
        )
        assert resp.status_code == 422

    db_path = data_root / "state" / "bolt.sqlite3"
    if db_path.exists():
        assert _SECRET_CANARY.encode() not in db_path.read_bytes()
