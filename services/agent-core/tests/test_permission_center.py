"""Tests for PermissionCenterService."""
import pytest
from dataclasses import dataclass

from bolt_core.permission_center import (
    PermissionCenterService,
    PermissionCenterItem,
    PermissionCenterSummary,
    _classify_risk,
    _risk_label,
)


@dataclass(frozen=True)
class FakePermission:
    id: str
    run_id: str
    tool: str
    operation: str
    payload: dict
    reason: str
    status: str


class FakePermissionQueue:
    def __init__(self, items=None):
        self._items = items or []

    def pending(self):
        return [i for i in self._items if i.status == "pending_permission"]


def make_perm(id_="p1", tool="shell_executor", operation="execute", reason="需要执行测试", payload=None):
    return FakePermission(
        id=id_, run_id="r1", tool=tool, operation=operation,
        payload=payload or {"cmd": "npm test"}, reason=reason, status="pending_permission",
    )


# ── Risk classification ─────────────────────────────────────────────────

def test_classify_shell_executor_as_high():
    assert _classify_risk("shell_executor", "run") == "high"


def test_classify_file_write_as_high():
    assert _classify_risk("file_writer", "write") == "high"


def test_classify_patch_engine_as_high():
    assert _classify_risk("patch_engine", "patch") == "high"


def test_classify_file_read_as_medium():
    assert _classify_risk("file_reader", "read") == "medium"


def test_classify_web_search_as_low():
    assert _classify_risk("web_search", "search") == "low"


def test_risk_label_chinese():
    assert _risk_label("high") == "高风险"
    assert _risk_label("medium") == "中风险"
    assert _risk_label("low") == "低风险"


# ── Service empty state ─────────────────────────────────────────────────

def test_empty_permissions():
    svc = PermissionCenterService(FakePermissionQueue())
    result = svc.get_summary()
    assert result.total_pending == 0
    assert result.high_risk_count == 0
    assert result.items == []


# ── Service with items ──────────────────────────────────────────────────

def test_single_high_risk():
    queue = FakePermissionQueue([make_perm("p1", "shell_executor", "execute")])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    assert result.total_pending == 1
    assert result.high_risk_count == 1
    assert len(result.items) == 1
    assert result.items[0].risk_level == "high"
    assert result.items[0].tool_cn == "命令行执行"


def test_mixed_risks():
    queue = FakePermissionQueue([
        make_perm("p1", "shell_executor", "execute"),
        make_perm("p2", "file_reader", "read"),
        make_perm("p3", "web_search", "search"),
    ])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    assert result.total_pending == 3
    assert result.high_risk_count == 1
    assert result.medium_risk_count == 1
    assert result.low_risk_count == 1


def test_items_sorted_high_first():
    queue = FakePermissionQueue([
        make_perm("p3", "web_search", "search"),
        make_perm("p1", "shell_executor", "execute"),
    ])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    assert result.items[0].risk_level == "high"
    assert result.items[1].risk_level == "low"


def test_chinese_fields_present():
    queue = FakePermissionQueue([make_perm("p1", "patch_engine", "patch")])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    item = result.items[0]
    assert item.risk_label_cn == "高风险"
    assert len(item.risk_explanation_cn) > 0
    assert len(item.impact_cn) > 0
    assert any('\u4e00' <= c <= '\u9fff' for c in item.tool_cn)


def test_to_dict():
    queue = FakePermissionQueue([make_perm("p1", "git", "commit")])
    svc = PermissionCenterService(queue)
    d = svc.get_summary().to_dict()
    assert d["total_pending"] == 1
    assert len(d["items"]) == 1
    assert "tool_cn" in d["items"][0]
    assert "risk_label_cn" in d["items"][0]


def test_handles_exceptions():
    class BrokenQueue:
        def pending(self):
            raise RuntimeError("broken")
    svc = PermissionCenterService(BrokenQueue())
    result = svc.get_summary()
    assert result.total_pending == 0
    assert result.items == []


# ── Payload redaction ──────────────────────────────────────────────────────

def test_payload_redacted_for_api_key_inline():
    # Realistic: API key appears inline in a shell command string
    queue = FakePermissionQueue([
        make_perm("p1", "shell_executor", "execute", reason="需要执行测试",
                  payload={"cmd": "API_KEY=sk-abc123def4567890 npm start"}),
    ])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    item = result.items[0]
    assert "sk-abc123def4567890" not in item.payload_summary
    assert "[已脱敏]" in item.payload_summary


def test_payload_redacted_for_token_inline():
    # Realistic: TOKEN appears inline in a curl command
    queue = FakePermissionQueue([
        make_perm("p1", "shell_executor", "execute", reason="需要执行测试",
                  payload={"cmd": "curl -H TOKEN=ghp_ABCDEF1234567890 http://api.example.com"}),
    ])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    item = result.items[0]
    assert "ghp_ABCDEF1234567890" not in item.payload_summary
    assert "[已脱敏]" in item.payload_summary


def test_payload_redacted_for_bearer():
    queue = FakePermissionQueue([
        make_perm("p1", "shell_executor", "execute", reason="需要执行测试",
                  payload={"headers": {"Authorization": "Bearer eyJhbGciOi..."}}),
    ])
    svc = PermissionCenterService(queue)
    result = svc.get_summary()
    item = result.items[0]
    assert "eyJhbGciOi" not in item.payload_summary
    assert "Bearer [已脱敏]" in item.payload_summary
