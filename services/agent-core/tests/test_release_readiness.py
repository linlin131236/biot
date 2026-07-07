"""Tests for ReleaseReadinessService."""
import json
import subprocess
from pathlib import Path

import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.release_readiness import ReleaseReadinessService


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Create a minimal project directory with git repo and docs."""
    d = tmp_path / "project"
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(d), capture_output=True)
    docs = d / "docs"
    docs.mkdir(parents=True)
    (docs / "project-state.md").write_text("# Bolt Project State\n## 当前稳定基线\n- 已完成到：M57", encoding="utf-8")
    (docs / "phase-57-review-gate.md").write_text("## 状态：已完成/已验证", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), capture_output=True)
    return d


@pytest.fixture
def clean_store(tmp_path):
    """Create a clean audit store with valid records."""
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    store.save_queue_items([{
        "id": "eq_0", "closure_id": "cl_0", "kind": "verification_command",
        "title": "验证", "description": "", "risk": "read_only",
        "status": "approved", "command": None, "reason": "", "result": "",
        "created_at": 1.0,
    }])
    store.save_handoff_records([{
        "id": "eh_0", "queue_item_id": "eq_0", "closure_id": "cl_0",
        "kind": "verification_command", "status": "completed",
        "handoff_type": "manual_verification", "title": "验证", "instruction": "",
        "command": None, "goal_objective": "", "run_id": None, "goal_id": None,
        "permission_request_id": None, "permission_status": "executed",
        "bridge_error": "", "permission_workspace": None, "result": "通过",
        "created_at": 1.0, "updated_at": 1.0,
    }])
    store.save_closure_records([{
        "id": "cl_0", "objective": "测试", "template_id": "test", "run_id": None,
        "goal_id": None, "status": "completed", "final_status": "completed",
        "plan_summary": "", "changed_files": [], "commands": ["pytest"],
        "command_results": ["491 passed"], "permission_request_ids": [],
        "retry_count": 0, "review_summary": "", "next_action": "",
        "created_at": 1.0,
    }])
    return store


def test_clean_state_returns_ready(project_dir, clean_store):
    """clean 状态返回 ready: true。"""
    svc = ReleaseReadinessService(str(project_dir), clean_store)
    result = svc.assess()
    assert result["ready"] is True


def test_damaged_audit_returns_not_ready(tmp_path):
    """有 integrity blocking 返回 ready: false。"""
    path = tmp_path / "execution-audit.json"
    path.write_text("not json {{{", encoding="utf-8")
    store = ExecutionAuditStore(path)
    d = tmp_path / "proj"
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(d), capture_output=True)
    (d / "docs").mkdir(parents=True)
    (d / "docs" / "project-state.md").write_text("ok", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), capture_output=True)
    svc = ReleaseReadinessService(str(d), store)
    result = svc.assess()
    assert result["ready"] is False


def test_secret_in_audit_returns_not_ready(tmp_path):
    """审计文件中有 secret 明文返回 ready: false。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({
        "version": 1,
        "queue_items": [],
        "handoff_records": [],
        "closure_records": [{"id": "cl_0", "command_results": ["OPENAI_API_KEY=sk-abc123def456789"]}],
    }, ensure_ascii=False), encoding="utf-8")
    store = ExecutionAuditStore(path)
    svc = ReleaseReadinessService(str(_make_git_repo(tmp_path, "proj_plain")), store)
    result = svc.assess()
    assert result["ready"] is False


def test_redacted_placeholders_do_not_trigger_secret_scan(tmp_path):
    """已脱敏占位符（如 TOKEN=[已脱敏]）不触发 secret scan 阻断。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({
        "version": 1,
        "queue_items": [],
        "handoff_records": [],
        "closure_records": [{"id": "cl_0", "command_results": [
            "TOKEN=[已脱敏]",
            "API_KEY=[已脱敏]",
            "OPENAI_API_KEY=[已脱敏]",
            "Bearer [已脱敏]",
            "SECRET=[已脱敏]",
            "PASSWORD=[已脱敏]",
        ]}],
    }, ensure_ascii=False), encoding="utf-8")
    store = ExecutionAuditStore(path)
    svc = ReleaseReadinessService(str(_make_git_repo(tmp_path, "proj_redacted")), store)
    result = svc.assess()

    # 不应有 secret 阻断
    secret_check = next((c for c in result["checks"] if c["code"] == "secret_scan"), None)
    assert secret_check is not None
    assert secret_check["passed"] is True, f"secret_scan should pass for redacted placeholders, got: {secret_check['detail']}"


def test_mixed_plaintext_and_redacted_detects_plaintext(tmp_path):
    """已脱敏 + 明文混合时仍能检测到明文。"""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({
        "version": 1,
        "queue_items": [],
        "handoff_records": [],
        "closure_records": [{"id": "cl_0", "command_results": [
            "TOKEN=[已脱敏]",
            "API_KEY=real_secret_abc123",
        ]}],
    }, ensure_ascii=False), encoding="utf-8")
    store = ExecutionAuditStore(path)
    svc = ReleaseReadinessService(str(_make_git_repo(tmp_path, "proj_mixed")), store)
    result = svc.assess()
    assert result["ready"] is False


def _make_git_repo(tmp_path, name):
    """Helper: create a minimal git repo with docs."""
    d = tmp_path / name
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(d), capture_output=True)
    (d / "docs").mkdir(parents=True)
    (d / "docs" / "project-state.md").write_text("ok", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), capture_output=True)
    return d


def test_result_structure_has_required_fields(project_dir, clean_store):
    """返回结果包含 ready, checks, blockers, warnings。"""
    svc = ReleaseReadinessService(str(project_dir), clean_store)
    result = svc.assess()
    assert "ready" in result
    assert "checks" in result
    assert "blockers" in result
    assert "warnings" in result
    assert isinstance(result["checks"], list)


def test_all_checks_have_chinese_labels(project_dir, clean_store):
    """所有检查项 label 为中文。"""
    svc = ReleaseReadinessService(str(project_dir), clean_store)
    result = svc.assess()
    for check in result["checks"]:
        assert "label" in check
        assert any('\u4e00' <= c <= '\u9fff' for c in check["label"]), f"label not Chinese: {check['label']}"


def test_readiness_service_is_read_only(project_dir, clean_store):
    """release readiness service 不写文件。"""
    svc = ReleaseReadinessService(str(project_dir), clean_store)
    before = clean_store._path.read_text(encoding="utf-8") if clean_store._path.exists() else ""
    svc.assess()
    after = clean_store._path.read_text(encoding="utf-8") if clean_store._path.exists() else ""
    assert before == after


def test_no_executable_commands_in_result(project_dir, clean_store):
    """返回结果不包含可执行命令。"""
    svc = ReleaseReadinessService(str(project_dir), clean_store)
    result = svc.assess()
    serialized = json.dumps(result, ensure_ascii=False)
    assert "shell.execute" not in serialized
    assert "runAgentLoop" not in serialized
    assert "approve_permission" not in serialized
    assert "git push" not in serialized
