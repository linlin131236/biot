"""Tests for CodeMapIndexService."""
import pytest

from bolt_core.code_map_index import CodeMapIndexService, CodeMapEntry, _classify_category


# ── Category classification ───────────────────────────────────────────

def test_classify_test_file():
    assert _classify_category("services/agent-core/tests/test_app.py") == "test"


def test_classify_service_file():
    assert _classify_category("services/agent-core/src/bolt_core/harness.py") == "service"


def test_classify_frontend_file():
    assert _classify_category("apps/desktop/src/App.tsx") == "frontend"


def test_classify_shared_file():
    assert _classify_category("packages/shared/src/protocol.ts") == "shared"


def test_classify_docs_file():
    assert _classify_category("docs/project-state.md") == "docs"


# ── Index building ────────────────────────────────────────────────────

def test_build_index_in_workspace():
    svc = CodeMapIndexService(".")
    count = svc.build_index()
    assert count > 0, "should index at least some files in the project"


def test_index_has_entries():
    svc = CodeMapIndexService(".")
    svc.build_index()
    entries = svc.list_entries()
    assert len(entries) > 0


def test_list_entries_by_category():
    svc = CodeMapIndexService(".")
    svc.build_index()
    for cat in ["service", "test", "frontend", "shared"]:
        entries = svc.list_entries(category=cat)
        for e in entries:
            assert e["category"] == cat, f"expected {cat}, got {e['category']} for {e['file_path']}"


def test_each_entry_has_required_fields():
    svc = CodeMapIndexService(".")
    svc.build_index()
    entries = svc.list_entries()
    for e in entries:
        for key in ["file_path", "module", "category", "symbols", "role_summary", "risk_hints", "source_refs"]:
            assert key in e, f"missing {key} in {e.get('file_path', '?')}"


def test_role_summaries_are_chinese():
    svc = CodeMapIndexService(".")
    svc.build_index()
    entries = svc.list_entries()
    chinese_count = 0
    for e in entries:
        if any('\u4e00' <= c <= '\u9fff' for c in e["role_summary"]):
            chinese_count += 1
    # At least some entries should have Chinese summaries
    assert chinese_count > 0


# ── Query ─────────────────────────────────────────────────────────────

def test_query_by_keyword():
    svc = CodeMapIndexService(".")
    svc.build_index()
    results = svc.query("harness")
    assert len(results) > 0


def test_query_case_insensitive():
    svc = CodeMapIndexService(".")
    svc.build_index()
    r1 = svc.query("Harness")
    r2 = svc.query("harness")
    assert len(r1) == len(r2)


def test_query_no_results():
    svc = CodeMapIndexService(".")
    svc.build_index()
    results = svc.query("xyznonexistent12345")
    assert results == []


# ── File summary ──────────────────────────────────────────────────────

def test_get_file_summary():
    svc = CodeMapIndexService(".")
    svc.build_index()
    result = svc.get_file_summary("services/agent-core/src/bolt_core/harness.py")
    assert result is not None
    assert result["category"] == "service"


def test_get_nonexistent_file():
    svc = CodeMapIndexService(".")
    svc.build_index()
    result = svc.get_file_summary("nonexistent/file.py")
    assert result is None


# ── Summary ───────────────────────────────────────────────────────────

def test_summary():
    svc = CodeMapIndexService(".")
    svc.build_index()
    s = svc.summary()
    assert "total_files" in s
    assert s["total_files"] > 0
    assert "by_category" in s
    assert "scope" in s


# ── Excluded paths ────────────────────────────────────────────────────

def test_no_node_modules_in_index():
    svc = CodeMapIndexService(".")
    svc.build_index()
    entries = svc.list_entries()
    for e in entries:
        assert "node_modules" not in e["file_path"]


def test_no_dist_in_index():
    svc = CodeMapIndexService(".")
    svc.build_index()
    entries = svc.list_entries()
    for e in entries:
        assert "dist/" not in e["file_path"] and "build/" not in e["file_path"]


def test_no_managed_runtime_payload_in_index():
    svc = CodeMapIndexService(".")
    payload = svc._workspace / "services/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/bin/Lib/site.py"
    assert svc._is_indexable(payload) is False


# ── Safety: read-only ─────────────────────────────────────────────────

def test_service_has_no_write_methods():
    svc = CodeMapIndexService(".")
    assert not hasattr(svc, "write")
    assert not hasattr(svc, "execute")
    assert not hasattr(svc, "delete")
