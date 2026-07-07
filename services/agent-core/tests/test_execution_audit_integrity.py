"""Tests for ExecutionAuditIntegrityService."""
import json

import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_audit_integrity import ExecutionAuditIntegrityService


def test_missing_file_returns_healthy(tmp_path):
    """审计文件不存在时返回空列表（健康状态）。"""
    path = tmp_path / "missing" / "execution-audit.json"
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    assert result == []


def test_damaged_json_returns_blocking_diagnostic(tmp_path):
    """JSON 损坏时返回阻断诊断。"""
    path = tmp_path / "execution-audit.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    assert len(result) == 1
    assert result[0]["severity"] == "blocking"
    assert result[0]["code"] == "json_damaged"
    assert "损坏" in result[0]["summary"]


def test_queue_items_not_list_returns_blocking(tmp_path):
    """queue_items 不是列表时返回阻断诊断。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({"version": 1, "queue_items": "not_a_list", "handoff_records": [], "closure_records": []}), encoding="utf-8")
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    assert len(result) >= 1
    blocking = [d for d in result if d["severity"] == "blocking"]
    assert len(blocking) >= 1
    assert any("queue" in d["code"].lower() for d in blocking)


def test_handoff_records_not_list_returns_blocking(tmp_path):
    """handoff_records 不是列表时返回阻断诊断。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({"version": 1, "queue_items": [], "handoff_records": 42, "closure_records": []}), encoding="utf-8")
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    assert len(result) >= 1
    blocking = [d for d in result if d["severity"] == "blocking"]
    assert len(blocking) >= 1
    assert any("handoff" in d["code"].lower() for d in blocking)


def test_closure_records_not_list_returns_blocking(tmp_path):
    """closure_records 不是列表时返回阻断诊断。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({"version": 1, "queue_items": [], "handoff_records": [], "closure_records": None}), encoding="utf-8")
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    assert len(result) >= 1
    blocking = [d for d in result if d["severity"] == "blocking"]
    assert len(blocking) >= 1
    assert any("closure" in d["code"].lower() for d in blocking)


def test_clean_file_returns_clean_status(tmp_path):
    """格式完整的文件返回干净状态。"""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    store.save_queue_items([{"id": "eq_0", "status": "approved"}])
    store.save_handoff_records([{"id": "eh_0", "status": "waiting_permission"}])
    store.save_closure_records([{"id": "cl_0", "objective": "测试"}])
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    blocking = [d for d in result if d["severity"] == "blocking"]
    assert len(blocking) == 0


def test_save_queue_preserves_handoff_and_closure(tmp_path):
    """保存 queue 不丢失 handoff/closure 记录。"""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    handoff = [{"id": "eh_1", "status": "waiting_permission"}]
    closure = [{"id": "cl_1", "objective": "测试"}]

    store.save_handoff_records(handoff)
    store.save_closure_records(closure)
    store.save_queue_items([{"id": "eq_1", "status": "approved"}])

    state = store.load()
    assert state.handoff_records == handoff
    assert state.closure_records == closure


def test_save_handoff_preserves_queue_and_closure(tmp_path):
    """保存 handoff 不丢失 queue/closure 记录。"""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    queue = [{"id": "eq_1", "status": "approved"}]
    closure = [{"id": "cl_1", "objective": "测试"}]

    store.save_queue_items(queue)
    store.save_closure_records(closure)
    store.save_handoff_records([{"id": "eh_1", "status": "waiting_permission"}])

    state = store.load()
    assert state.queue_items == queue
    assert state.closure_records == closure


def test_save_closure_preserves_queue_and_handoff(tmp_path):
    """保存 closure 不丢失 queue/handoff 记录。"""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    queue = [{"id": "eq_1", "status": "approved"}]
    handoff = [{"id": "eh_1", "status": "waiting_permission"}]

    store.save_queue_items(queue)
    store.save_handoff_records(handoff)
    store.save_closure_records([{"id": "cl_1", "objective": "测试"}])

    state = store.load()
    assert state.queue_items == queue
    assert state.handoff_records == handoff


def test_integrity_service_is_read_only(tmp_path):
    """integrity service 不写文件、不修改文件。"""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    store.save_queue_items([{"id": "eq_0", "status": "approved"}])
    original_content = path.read_text(encoding="utf-8")
    service = ExecutionAuditIntegrityService(store)

    service.list_integrity()

    assert path.read_text(encoding="utf-8") == original_content


def test_all_severity_labels_are_chinese(tmp_path):
    """所有 severity_label 必须是中文。"""
    path = tmp_path / "execution-audit.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    store = ExecutionAuditStore(path)
    service = ExecutionAuditIntegrityService(store)

    result = service.list_integrity()

    for item in result:
        assert item["severity_label"] in ("阻断", "警告", "提示"), f"unexpected label: {item['severity_label']}"
        for key in ("summary", "suggestion"):
            assert item[key], f"empty {key}"
