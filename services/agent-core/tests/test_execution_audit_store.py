import json

import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore, ExecutionAuditStoreError


def test_missing_audit_file_loads_empty_state(tmp_path):
    store = ExecutionAuditStore(tmp_path / "state" / "execution-audit.json")

    state = store.load()

    assert state.queue_items == []
    assert state.handoff_records == []


def test_saved_queue_items_and_handoff_records_reload(tmp_path):
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    queue_items = [{"id": "eq_0", "status": "approved"}]
    handoff_records = [{"id": "eh_0", "status": "ready_for_manual_action"}]

    store.save_queue_items(queue_items)
    store.save_handoff_records(handoff_records)

    state = ExecutionAuditStore(path).load()
    assert state.queue_items == queue_items
    assert state.handoff_records == handoff_records


def test_saving_queue_and_handoffs_preserves_closure_records(tmp_path):
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    closure_records = [{"id": "cl_1", "objective": "修复拼写"}]

    store.save_closure_records(closure_records)
    store.save_queue_items([{"id": "eq_0", "status": "approved"}])
    store.save_handoff_records([{"id": "eh_0", "status": "waiting_permission"}])

    assert ExecutionAuditStore(path).load().closure_records == closure_records


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "state" / "execution-audit.json"
    store = ExecutionAuditStore(path)

    store.save_queue_items([])

    assert path.exists()


def test_damaged_json_raises_clear_error(tmp_path):
    path = tmp_path / "execution-audit.json"
    path.write_text("{", encoding="utf-8")
    store = ExecutionAuditStore(path)

    with pytest.raises(ExecutionAuditStoreError, match="execution audit JSON is damaged"):
        store.load()


def test_saved_content_does_not_include_sensitive_runtime_words(tmp_path):
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)

    store.save_queue_items([{
        "id": "eq_0",
        "closure_id": "cl_1",
        "kind": "manual_review",
        "title": "补充验证证据",
        "description": "缺少证据",
        "risk": "read_only",
        "status": "pending",
        "command": None,
        "reason": "",
        "result": "",
        "created_at": 1.0,
    }])

    content = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(content, ensure_ascii=False)
    assert "process" not in serialized
    assert "env" not in serialized
    assert "token" not in serialized
    assert "cert" not in serialized
