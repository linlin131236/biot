"""Integration tests: secrets must not leak into closure, handoff, or timeline."""
import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.task_closure_service import TaskClosureService


def _make_store(tmp_path):
    return ExecutionAuditStore(tmp_path / "execution-audit.json")


def _make_closures(store):
    svc = TaskClosureService(store)
    closure = svc.start(objective="修复拼写", template_id="test")
    return svc, closure.id


def _make_queue_item(store, closure_id):
    queue = ExecutionQueueService(store)
    return queue.create_item(
        closure_id=closure_id,
        kind="verification_command",
        title="验证",
        description="测试",
        risk="read_only",
        command=None,
        reason="",
    )


def _make_handoff(store, queue_item):
    handoffs = ExecutionHandoffService(store)
    return handoffs.create_from_queue_item(queue_item)


def test_closure_record_command_redacts_secrets(tmp_path):
    """record_command 将敏感值脱敏后保存。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)

    sensitive_cmd = "OPENAI_API_KEY=sk-proj-abc123def456789 uv run test"
    sensitive_result = "Bearer eyJhbGciOiJIUzI1NiJ9.token SECRET=mysecret output"

    closures.record_command(cid, sensitive_cmd, sensitive_result)
    saved = closures.load(cid)

    assert "OPENAI_API_KEY=[已脱敏]" in saved.commands[0]
    assert "sk-proj-abc123def456789" not in saved.commands[0]
    assert "Bearer [已脱敏]" in saved.command_results[0]
    assert "SECRET=[已脱敏]" in saved.command_results[0]
    assert "mysecret" not in saved.command_results[0]
    assert "output" in saved.command_results[0]


def test_handoff_result_redacts_secrets(tmp_path):
    """handoff complete/fail 的 result 被脱敏。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)
    queue = ExecutionQueueService(store)
    qi = queue.create_item(closure_id=cid, kind="verification_command", title="验证", description="测试", risk="read_only", command=None, reason="")
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(qi)
    hid = record.id

    handoffs.complete(hid, "API_KEY=abc TOKEN=def result ok")
    saved = handoffs.get_record(hid)

    assert "API_KEY=[已脱敏]" in saved.result
    assert "TOKEN=[已脱敏]" in saved.result
    assert "abc" not in saved.result
    assert "result ok" in saved.result


def test_handoff_bridge_error_redacts_secrets(tmp_path):
    """bridge_error 脱敏。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)
    queue = ExecutionQueueService(store)
    qi = queue.create_item(closure_id=cid, kind="verification_command", title="验证", description="测试", risk="read_only", command=None, reason="")
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(qi)
    hid = record.id

    handoffs.mark_bridge_failed(hid, "failed", "PASSWORD=admin123 permission denied")
    saved = handoffs.get_record(hid)

    assert "PASSWORD=[已脱敏]" in saved.bridge_error
    assert "admin123" not in saved.bridge_error


def test_audit_file_json_no_secrets(tmp_path):
    """持久化 audit JSON 不含明文敏感值。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)
    closures.record_command(cid, "echo test", "TOKEN=ghp_secret_token_value12 result")

    store_path = store._path
    raw = store_path.read_text(encoding="utf-8")
    assert "ghp_secret_token_value12" not in raw
    assert "[已脱敏]" in raw


def test_preserves_non_sensitive_output(tmp_path):
    """非敏感输出完整保留。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)
    closures.record_command(cid, "pnpm test", "491 passed, 0 failed")

    saved = closures.load(cid)
    assert saved.commands[0] == "pnpm test"
    assert "491 passed, 0 failed" in saved.command_results[0]


def test_preserves_chinese_text(tmp_path):
    """中文文案不受影响。"""
    store = _make_store(tmp_path)
    closures, cid = _make_closures(store)
    closures.record_command(cid, "echo 测试", "执行完成：验证通过")

    saved = closures.load(cid)
    assert "测试" in saved.commands[0]
    assert "验证通过" in saved.command_results[0]
