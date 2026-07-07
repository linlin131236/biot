"""API tests for Task Home endpoint."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /task-home ──────────────────────────────────────────────────────

def test_get_task_home_returns_200(client):
    resp = client.get("/task-home")
    assert resp.status_code == 200
    data = resp.json()
    assert "unfinished_goal_count" in data
    assert "pending_permission_count" in data
    assert "blocker_count" in data
    assert "warning_count" in data
    assert "active_task_count" in data
    assert "next_suggestions" in data
    assert "recent_events" in data
    assert "updated_at" in data


def test_task_home_unfinished_goal_count_is_int(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["unfinished_goal_count"], int)


def test_task_home_pending_permission_count_is_int(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["pending_permission_count"], int)


def test_task_home_blocker_count_is_int(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["blocker_count"], int)


def test_task_home_warning_count_is_int(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["warning_count"], int)


def test_task_home_active_task_count_is_int(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["active_task_count"], int)


def test_task_home_suggestions_are_chinese(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["next_suggestions"], list)
    for s in data["next_suggestions"]:
        assert any('\u4e00' <= c <= '\u9fff' for c in s)


def test_task_home_current_goal_field(client):
    resp = client.get("/task-home")
    data = resp.json()
    # current_goal may be null if no running goal
    assert "current_goal" in data


def test_task_home_is_read_only(client):
    """POST/PUT/DELETE should not be allowed on /task-home."""
    resp_post = client.post("/task-home", json={})
    assert resp_post.status_code in (405, 404)
    resp_put = client.put("/task-home", json={})
    assert resp_put.status_code in (405, 404)
    resp_delete = client.delete("/task-home")
    assert resp_delete.status_code in (405, 404)


def test_task_home_recent_events_is_list(client):
    resp = client.get("/task-home")
    data = resp.json()
    assert isinstance(data["recent_events"], list)
