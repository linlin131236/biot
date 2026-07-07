"""Unit tests for LocalReleaseChecklistService. Read-only only."""
import json
import subprocess

import pytest

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.local_release_checklist import LocalReleaseChecklistService


def _make_git_repo(tmp_path, name: str) -> str:
    """Create a minimal git repo with committed docs for testing."""
    d = tmp_path / name
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(d), capture_output=True)
    (d / "docs").mkdir(parents=True)
    (d / "docs" / "project-state.md").write_text("# Bolt Project State\n- 已完成到：M57", encoding="utf-8")
    (d / "docs" / "phase-57-review-gate.md").write_text("## 状态", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), capture_output=True)
    return str(d)


@pytest.fixture
def project_dir(tmp_path):
    return _make_git_repo(tmp_path, "proj")


@pytest.fixture
def clean_store(tmp_path):
    path = tmp_path / "execution-audit.json"
    return ExecutionAuditStore(path)


def test_clean_state_returns_ready(project_dir, clean_store):
    """Clean state returns ready: true with all items pass."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    result = svc.checklist()
    assert result["ready"] is True
    assert len(result["items"]) > 0
    assert len(result["blockers"]) == 0
    assert result["disclaimer"] != ""


def test_checklist_has_required_fields(project_dir, clean_store):
    """Checklist result has all required top-level fields."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    result = svc.checklist()
    assert "ready" in result
    assert "items" in result
    assert "blockers" in result
    assert "warnings" in result
    assert "next_step" in result
    assert "disclaimer" in result


def test_checklist_items_have_required_fields(project_dir, clean_store):
    """Each checklist item has required fields."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    result = svc.checklist()
    for item in result["items"]:
        assert "code" in item
        assert "category" in item
        assert "label" in item
        assert "status" in item
        assert "status_label" in item
        assert "detail" in item
        assert "recommendation" in item  # can be None


def test_damaged_audit_returns_blocker(tmp_path):
    """Damaged audit file returns fail item and blocker."""
    path = tmp_path / "execution-audit.json"
    path.write_text("not json {{{", encoding="utf-8")
    store = ExecutionAuditStore(path)
    proj = _make_git_repo(tmp_path, "damaged")
    svc = LocalReleaseChecklistService(proj, store)
    result = svc.checklist()
    assert result["ready"] is False
    assert len(result["blockers"]) > 0
    audit_item = next((i for i in result["items"] if i["code"] == "audit_structure"), None)
    assert audit_item is not None
    assert audit_item["status"] == "fail"


def test_secret_in_audit_returns_blocker(tmp_path):
    """Audit with plaintext secret returns fail item and blocker."""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({
        "version": 1,
        "queue_items": [],
        "handoff_records": [],
        "closure_records": [{"id": "cl_0", "command_results": ["OPENAI_API_KEY=sk-abc123def456789"]}],
    }), encoding="utf-8")
    store = ExecutionAuditStore(path)
    proj = _make_git_repo(tmp_path, "secret")
    svc = LocalReleaseChecklistService(proj, store)
    result = svc.checklist()
    assert result["ready"] is False
    secret_item = next((i for i in result["items"] if i["code"] == "secret_scan"), None)
    assert secret_item is not None
    assert secret_item["status"] == "fail"


def test_redacted_placeholders_pass_secret_scan(tmp_path):
    """Redacted placeholders do NOT trigger secret scan fail."""
    path = tmp_path / "execution-audit.json"
    path.write_text(json.dumps({
        "version": 1,
        "queue_items": [],
        "handoff_records": [],
        "closure_records": [{"id": "cl_0", "command_results": [
            "TOKEN=[已脱敏]",
            "API_KEY=[已脱敏]",
            "Bearer [已脱敏]",
        ]}],
    }), encoding="utf-8")
    store = ExecutionAuditStore(path)
    proj = _make_git_repo(tmp_path, "redacted")
    svc = LocalReleaseChecklistService(proj, store)
    result = svc.checklist()
    secret_item = next((i for i in result["items"] if i["code"] == "secret_scan"), None)
    assert secret_item is not None
    assert secret_item["status"] == "pass", f"expected pass for redacted, got: {secret_item['detail']}"


def test_docs_missing_returns_warning(tmp_path):
    """Missing docs returns warning item."""
    d = tmp_path / "nodocs"
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=str(d), capture_output=True)
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    svc = LocalReleaseChecklistService(str(d), store)
    result = svc.checklist()
    docs_item = next((i for i in result["items"] if i["code"] == "docs_state"), None)
    assert docs_item is not None
    assert docs_item["status"] == "warn"


def test_review_gate_missing_returns_warning(tmp_path):
    """Missing review gate returns warning item."""
    d = tmp_path / "nogate"
    d.mkdir()
    subprocess.run(["git", "init"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(d), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(d), capture_output=True)
    (d / "docs").mkdir(parents=True)
    (d / "docs" / "project-state.md").write_text("已完成到：M57", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), capture_output=True)
    path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(path)
    svc = LocalReleaseChecklistService(str(d), store)
    result = svc.checklist()
    gate_item = next((i for i in result["items"] if i["code"] == "review_gate"), None)
    assert gate_item is not None
    assert gate_item["status"] == "warn"


def test_release_confirm_item_always_pass(project_dir, clean_store):
    """Release confirmation item always passes (read-only only)."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    result = svc.checklist()
    confirm = next((i for i in result["items"] if i["code"] == "release_confirm"), None)
    assert confirm is not None
    assert confirm["status"] == "pass"
    assert "只读" in confirm["detail"]


def test_checklist_is_read_only(project_dir, clean_store):
    """Multiple calls return consistent results (no side effects)."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    r1 = svc.checklist()
    r2 = svc.checklist()
    assert r1 == r2


def test_next_step_when_ready(project_dir, clean_store):
    """When ready, next_step mentions 爸爸 and manual release."""
    svc = LocalReleaseChecklistService(project_dir, clean_store)
    result = svc.checklist()
    assert "爸爸" in result["next_step"] or "人工" in result["next_step"]
    assert "终端" in result["next_step"] or "手动" in result["next_step"] or "人工" in result["next_step"]
