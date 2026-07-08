"""Tests for ResearcherIntegrationService."""
import pytest

from bolt_core.researcher_integration import (
    ResearcherIntegrationService,
    ResearchScope,
    ResearchBrief,
    ResearchSummary,
    ResearchValidation,
)


# ── ResearchScope ──────────────────────────────────────────────────────

def test_scope_labels_chinese():
    assert ResearchScope.PROJECT_DOCS.label_cn == "项目文档"
    assert ResearchScope.BINCLOUD_REFS.label_cn == "BinCloud 参考资料"
    assert ResearchScope.CODE_MAP.label_cn == "代码地图"
    assert ResearchScope.DECISION_MEMORY.label_cn == "决策记忆"
    assert ResearchScope.FAILURE_MEMORY.label_cn == "失败记忆"


def test_scope_values():
    scopes = list(ResearchScope)
    assert len(scopes) == 5


# ── Data models ────────────────────────────────────────────────────────

def test_brief_to_dict():
    b = ResearchBrief(
        brief_id="rb-001", title_cn="测试", question_cn="问题",
        allowed_sources=["doc1.md", "doc2.md"],
        scope=ResearchScope.PROJECT_DOCS,
        created_at="2026-07-07T00:00:00Z",
    )
    d = b.to_dict()
    assert d["brief_id"] == "rb-001"
    assert d["scope"] == "project_docs"
    assert d["scope_label_cn"] == "项目文档"


def test_summary_to_dict():
    s = ResearchSummary(
        brief_id="rb-001", summary_cn="摘要内容",
        principles_cn=["原则1"], risks_cn=["风险1"],
        source_refs=["doc1.md", "doc2.md"],
        scope=ResearchScope.DECISION_MEMORY,
        findings_count=2,
    )
    d = s.to_dict()
    assert d["summary_cn"] == "摘要内容"
    assert d["findings_count"] == 2


# ── Service: create_brief ──────────────────────────────────────────────

def test_create_brief_valid():
    svc = ResearcherIntegrationService()
    result = svc.create_brief("测试", "问题?", ["doc1.md", "doc2.md"], "project_docs")
    assert hasattr(result, 'brief_id')
    assert result.title_cn == "测试"
    assert result.scope == ResearchScope.PROJECT_DOCS


def test_create_brief_too_many_sources():
    svc = ResearcherIntegrationService()
    result = svc.create_brief("测试", "问题?", ["a", "b", "c", "d", "e"], "project_docs")
    assert result.valid is False
    assert result.blocked is True


def test_create_brief_no_sources():
    svc = ResearcherIntegrationService()
    result = svc.create_brief("测试", "问题?", [], "project_docs")
    assert result.valid is False
    assert result.blocked is True


def test_create_brief_invalid_scope():
    svc = ResearcherIntegrationService()
    result = svc.create_brief("测试", "问题?", ["a", "b"], "invalid_scope")
    assert result.valid is False
    assert result.blocked is True


def test_create_brief_unique_ids():
    svc = ResearcherIntegrationService()
    r1 = svc.create_brief("a", "q", ["d1", "d2"], "code_map")
    r2 = svc.create_brief("b", "q", ["d1", "d2"], "code_map")
    assert r1.brief_id != r2.brief_id


# ── Service: produce_summary ───────────────────────────────────────────

def test_produce_summary_valid():
    svc = ResearcherIntegrationService()
    brief = svc.create_brief("测试", "问题?", ["doc1.md", "doc2.md"], "project_docs")
    result = svc.produce_summary(
        brief.brief_id, "中文摘要", ["原则"], ["风险"],
        ["doc1.md", "doc2.md"],
    )
    assert result.summary_cn == "中文摘要"
    assert result.source_refs == ["doc1.md", "doc2.md"]


def test_produce_summary_no_source_refs():
    svc = ResearcherIntegrationService()
    brief = svc.create_brief("测试", "问题?", ["doc1.md", "doc2.md"], "project_docs")
    result = svc.produce_summary(
        brief.brief_id, "摘要", ["原则"], ["风险"], [],
    )
    assert result.valid is False
    assert result.blocked is True


def test_produce_summary_no_summary_cn():
    svc = ResearcherIntegrationService()
    brief = svc.create_brief("测试", "问题?", ["doc1.md", "doc2.md"], "project_docs")
    result = svc.produce_summary(
        brief.brief_id, "", ["原则"], ["风险"], ["doc1.md"],
    )
    assert result.valid is False


def test_produce_summary_brief_not_found():
    svc = ResearcherIntegrationService()
    result = svc.produce_summary(
        "nonexistent", "摘要", [], [], ["doc1.md"],
    )
    assert result.valid is False


def test_produce_summary_extra_sources_warning():
    svc = ResearcherIntegrationService()
    brief = svc.create_brief("测试", "问题?", ["doc1.md", "doc2.md"], "project_docs")
    result = svc.produce_summary(
        brief.brief_id, "摘要", ["原则"], ["风险"],
        ["doc1.md", "doc2.md", "extra.md"],
    )
    # Should succeed but with warning in details
    assert result.summary_cn == "摘要"


# ── Service: read ──────────────────────────────────────────────────────

def test_list_briefs():
    svc = ResearcherIntegrationService()
    svc.create_brief("a", "q", ["d1", "d2"], "code_map")
    svc.create_brief("b", "q", ["d1", "d2"], "code_map")
    assert len(svc.list_briefs()) == 2


def test_get_brief():
    svc = ResearcherIntegrationService()
    brief = svc.create_brief("测试", "q", ["d1", "d2"], "decision_memory")
    found = svc.get_brief(brief.brief_id)
    assert found is not None
    assert found.title_cn == "测试"


# ── Service: validate_source_refs ──────────────────────────────────────

def test_validate_source_refs_empty():
    svc = ResearcherIntegrationService()
    result = svc.validate_source_refs([])
    assert result.valid is False
    assert result.blocked is True


def test_validate_source_refs_valid():
    svc = ResearcherIntegrationService()
    result = svc.validate_source_refs(["doc1.md", "doc2.md"])
    assert result.valid is True


# ── scope_options ──────────────────────────────────────────────────────

def test_scope_options():
    svc = ResearcherIntegrationService()
    options = svc.scope_options()
    assert len(options) == 5
    assert any(o["scope"] == "project_docs" for o in options)


# ── ResearcherEngine.execute_brief (M159) ────────────────────────────────

def test_execute_brief_unknown_brief_returns_validation_error():
    from bolt_core.researcher_integration import ResearcherEngine
    svc = ResearcherIntegrationService()
    engine = ResearcherEngine(svc)
    result = engine.execute_brief("nonexistent")
    assert hasattr(result, 'valid')
    assert result.valid is False
    assert "未找到研究摘要" in result.message_cn


def test_execute_brief_code_map_scope():
    from bolt_core.researcher_integration import ResearcherEngine

    class FakeCodeMap:
        def query(self, keyword):
            return [{"path": "services/agent-core/src/bolt_core/permission_center.py", "risk": "permission"}]

    svc = ResearcherIntegrationService()
    brief = svc.create_brief(
        title_cn="权限中心研究",
        question_cn="权限中心如何工作",
        allowed_sources=["code_map"],
        scope="code_map",
    )
    engine = ResearcherEngine(svc, code_map=FakeCodeMap())
    result = engine.execute_brief(brief.brief_id)
    assert hasattr(result, 'source_refs')
    assert len(result.source_refs) > 0
    assert result.findings_count > 0


def test_execute_brief_decision_memory_scope():
    from bolt_core.researcher_integration import ResearcherEngine

    class FakeDecisionMemory:
        def query_by_keyword(self, keyword):
            return [type("Record", (), {"milestone": "M92"})(), type("Record", (), {"milestone": "M92"})()]

    svc = ResearcherIntegrationService()
    brief = svc.create_brief(
        title_cn="决策记忆研究",
        question_cn="权限中心相关决策",
        allowed_sources=["decision_memory"],
        scope="decision_memory",
    )
    engine = ResearcherEngine(svc, decision_memory=FakeDecisionMemory())
    result = engine.execute_brief(brief.brief_id)
    assert hasattr(result, 'source_refs')
    assert any("decision" in ref for ref in result.source_refs)


def test_execute_brief_failure_memory_scope():
    from bolt_core.researcher_integration import ResearcherEngine

    class FakeFailureMemory:
        def query_by_keyword(self, keyword):
            return [type("Record", (), {"category": "permission"})(), type("Record", (), {"category": "shell"})()]

    svc = ResearcherIntegrationService()
    brief = svc.create_brief(
        title_cn="失败模式研究",
        question_cn="权限相关失败",
        allowed_sources=["failure_memory"],
        scope="failure_memory",
    )
    engine = ResearcherEngine(svc, failure_memory=FakeFailureMemory())
    result = engine.execute_brief(brief.brief_id)
    assert hasattr(result, 'source_refs')
    assert any("failure" in ref for ref in result.source_refs)


def test_execute_brief_respects_max_sources():
    from bolt_core.researcher_integration import ResearcherEngine

    class FakeCodeMap:
        def query(self, keyword):
            return [{"path": f"file_{i}.py"} for i in range(10)]

    svc = ResearcherIntegrationService()
    brief = svc.create_brief(
        title_cn="代码研究",
        question_cn="权限相关代码",
        allowed_sources=["code_map"],
        scope="code_map",
    )
    engine = ResearcherEngine(svc, code_map=FakeCodeMap())
    result = engine.execute_brief(brief.brief_id)
    assert len(result.source_refs) <= 4


def test_execute_brief_synthesizes_risks():
    from bolt_core.researcher_integration import ResearcherEngine

    class FakeFailureMemory:
        def query_by_keyword(self, keyword):
            return [type("Record", (), {"category": "permission"})(), type("Record", (), {"category": "ipcRenderer"})(), type("Record", (), {"category": "push"})()]

    svc = ResearcherIntegrationService()
    brief = svc.create_brief(
        title_cn="风险研究",
        question_cn="安全风险",
        allowed_sources=["failure_memory"],
        scope="failure_memory",
    )
    engine = ResearcherEngine(svc, failure_memory=FakeFailureMemory())
    result = engine.execute_brief(brief.brief_id)
    assert hasattr(result, 'risks_cn')
    assert len(result.risks_cn) > 0
