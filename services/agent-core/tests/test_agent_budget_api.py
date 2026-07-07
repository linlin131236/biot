"""API tests for agent budget endpoints. Validates HTTP layer and safety."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


# ── Happy path ────────────────────────────────────────────────────────

def test_check_allowed():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_steps": 10},
        "state": {"steps_used": 5},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


def test_check_blocked_steps():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_steps": 5},
        "state": {"steps_used": 10},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["dimension"] == "steps"


def test_check_blocked_tool_calls():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_tool_calls": 3},
        "state": {"tool_calls_used": 5},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["dimension"] == "tool_calls"


def test_check_blocked_runtime():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_runtime_seconds": 30},
        "state": {"elapsed_seconds": 60},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["dimension"] == "runtime"


def test_check_blocked_context_tokens():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_context_tokens": 1000},
        "state": {"context_tokens_used": 2000},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["dimension"] == "context_tokens"


def test_check_defaults_applied():
    """When no config provided, safe defaults are used."""
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "state": {"steps_used": 0},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    # Should have default config in response
    assert data["config"]["max_steps"] > 0


def test_check_chinese_blocking_message():
    """Blocked results must have Chinese explanation."""
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_steps": 1},
        "state": {"steps_used": 5},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert any('\u4e00' <= c <= '\u9fff' for c in data["explanation"])
    assert any('\u4e00' <= c <= '\u9fff' for c in data["suggestion"])


# ── check-single endpoint ─────────────────────────────────────────────

def test_check_single_allowed():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check-single", json={
        "dimension": "custom_limit",
        "used": 5,
        "limit": 10,
        "label_cn": "自定义限制",
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True


def test_check_single_blocked():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check-single", json={
        "dimension": "custom",
        "used": 10,
        "limit": 5,
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False


# ── defaults endpoint ─────────────────────────────────────────────────

def test_get_defaults():
    client = TestClient(create_app())
    resp = client.get("/agent-budget/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_steps"] > 0
    assert data["max_tool_calls"] > 0
    assert data["max_runtime_seconds"] > 0
    assert data["max_context_tokens"] > 0


# ── Error cases ───────────────────────────────────────────────────────

def test_check_missing_state():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_steps": 5},
    })
    assert resp.status_code == 200  # defaults to zeros, which is allowed


def test_check_single_missing_dimension():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check-single", json={
        "used": 5, "limit": 10,
    })
    assert resp.status_code == 400


def test_check_single_invalid_numbers():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check-single", json={
        "dimension": "x",
        "used": "not-a-number",
        "limit": 10,
    })
    assert resp.status_code == 400


# ── Response shape ────────────────────────────────────────────────────

def test_check_response_has_all_fields():
    client = TestClient(create_app())
    resp = client.post("/agent-budget/check", json={
        "config": {"max_steps": 10},
        "state": {"steps_used": 5},
    })
    data = resp.json()
    for key in ["allowed", "dimension", "explanation", "suggestion", "config", "state"]:
        assert key in data, f"missing: {key}"


# ── Safety: no auto-increase endpoint ─────────────────────────────────

def test_no_auto_increase_endpoint():
    """There should be no endpoint that auto-increases budget."""
    client = TestClient(create_app())
    resp = client.post("/agent-budget/increase", json={})
    assert resp.status_code == 404
