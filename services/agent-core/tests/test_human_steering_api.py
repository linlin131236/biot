"""API tests for human steering endpoint. Validates HTTP layer and safety."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── Happy path ────────────────────────────────────────────────────────

def test_steer_continue():
    """Steering with continue intent returns 200 with proper result."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_1/steering", json={"content": "继续执行"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "continue"
    assert data["requires_human_confirmation"] is False
    assert data["intent_label"] == "继续"


def test_steer_pause():
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_2/steering", json={"content": "暂停任务"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "pause"


def test_steer_pause_with_node_info():
    """Pause with node info integrates with M66."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_3/steering", json={
        "content": "暂停",
        "node_id": "node_m66",
        "current_status": "running",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "pause"
    # With M66 integration, should mention snapshot
    assert "快照" in data["explanation"] or "M66" in data["explanation"]


def test_steer_change_goal():
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_4/steering", json={"content": "改成只改文档"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "change_goal"
    assert data["requires_human_confirmation"] is True
    assert len(data["pending_actions"]) > 0


def test_steer_request_review():
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_5/steering", json={"content": "帮我检查代码"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "request_review"


def test_steer_abort():
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_6/steering", json={"content": "取消任务"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "abort"
    assert data["requires_human_confirmation"] is True


def test_steer_unknown():
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_7/steering", json={"content": "xyz123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "unknown"
    assert "无法识别" in data["explanation"]


# ── Error cases ───────────────────────────────────────────────────────

def test_steer_empty_content():
    """Empty content should return 400."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_8/steering", json={"content": ""})
    assert resp.status_code == 400
    assert "不能为空" in str(resp.json().get("detail", ""))


def test_steer_whitespace_content():
    """Whitespace-only content should return 400."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_9/steering", json={"content": "   "})
    assert resp.status_code == 400


def test_steer_missing_content():
    """Missing content field should return 400."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_10/steering", json={})
    assert resp.status_code == 400


# ── Response shape ────────────────────────────────────────────────────

def test_steer_response_has_all_fields():
    """Response must contain all required SteeringResult fields."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_11/steering", json={"content": "继续"})
    assert resp.status_code == 200
    data = resp.json()
    required = ["intent", "intent_label", "explanation", "requires_human_confirmation",
                "action_taken", "pending_actions", "evidence_ref", "timestamp"]
    for key in required:
        assert key in data, f"missing: {key}"


def test_steer_chinese_response():
    """All user-visible text must be Chinese."""
    client = TestClient(create_app())
    resp = client.post("/runs/run_test_12/steering", json={"content": "继续"})
    assert resp.status_code == 200
    data = resp.json()
    # intent_label, explanation, action_taken should all contain Chinese chars
    for field in ["intent_label", "explanation", "action_taken"]:
        text = str(data.get(field, ""))
        assert any('\u4e00' <= c <= '\u9fff' for c in text), \
            f"field '{field}' has no Chinese characters: {text}"


# ── Safety invariants ─────────────────────────────────────────────────

def test_steer_never_returns_executable_instructions():
    """Steering result must never contain shell commands or executable instructions."""
    client = TestClient(create_app())
    intents_to_test = ["继续", "暂停", "改成xxx", "检查", "取消", "xyz"]
    for content in intents_to_test:
        resp = client.post("/runs/run_safety/steering", json={"content": content})
        assert resp.status_code == 200
        data = resp.json()
        full_text = str(data)
        # Must not contain shell execution patterns
        assert "rm -rf" not in full_text
        assert "subprocess" not in full_text.lower()
        assert "os.system" not in full_text
