"""ResearcherEngine: executes research briefs by querying data stores.
Extracted from researcher_integration.py (M159).

Read-only. Never modifies files, executes tools, or approves permissions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from bolt_core.researcher_integration import ResearchScope, _MAX_SOURCES, _MIN_SOURCES


@runtime_checkable
class _CodeMapQuery(Protocol):
    def query(self, keyword: str) -> list[dict]: ...

@runtime_checkable
class _DecisionMemoryQuery(Protocol):
    def query_by_keyword(self, keyword: str) -> list: ...

@runtime_checkable
class _FailureMemoryQuery(Protocol):
    def query_by_keyword(self, keyword: str) -> list: ...


class ResearcherEngine:
    """Executes research briefs by querying data stores and producing summaries."""

    def __init__(
        self,
        service,
        code_map: _CodeMapQuery | None = None,
        decision_memory: _DecisionMemoryQuery | None = None,
        failure_memory: _FailureMemoryQuery | None = None,
        docs_dir: Path | None = None,
        workspace: Path | None = None,
    ) -> None:
        self._service = service
        self._code_map = code_map
        self._decision_memory = decision_memory
        self._failure_memory = failure_memory
        self._docs_dir = docs_dir or (workspace / "docs" if workspace else None)

    def execute_brief(self, brief_id: str):
        """Execute a research brief by querying data stores and producing a summary."""
        brief = self._service.get_brief(brief_id)
        if brief is None:
            from bolt_core.researcher_integration import ResearchValidation
            return ResearchValidation(
                valid=False,
                message_cn=f"未找到研究摘要：{brief_id}。",
                blocked=True,
            )

        keywords = self._extract_keywords(brief.question_cn)
        findings: dict[str, list] = {}
        source_refs: list[str] = []

        if brief.scope == ResearchScope.CODE_MAP and self._code_map:
            for kw in keywords[:3]:
                results = self._code_map.query(kw)
                if results:
                    findings["code_map"] = results[:5]
                    source_refs.extend(f"code_map:{r.get('path', kw)}" for r in results[:3])

        if brief.scope == ResearchScope.DECISION_MEMORY and self._decision_memory:
            for kw in keywords[:3]:
                results = self._decision_memory.query_by_keyword(kw)
                if results:
                    findings["decision_memory"] = results[:5]
                    for r in results[:3]:
                        ref = getattr(r, "milestone", "") or kw
                        source_refs.append(f"decision:{ref}")

        if brief.scope == ResearchScope.FAILURE_MEMORY and self._failure_memory:
            for kw in keywords[:3]:
                results = self._failure_memory.query_by_keyword(kw)
                if results:
                    findings["failure_memory"] = results[:5]
                    for r in results[:3]:
                        ref = getattr(r, "category", "") or kw
                        source_refs.append(f"failure:{ref}")

        if brief.scope == ResearchScope.PROJECT_DOCS and self._docs_dir:
            doc_refs = self._read_project_docs(keywords[:3])
            if doc_refs:
                findings["project_docs"] = doc_refs
                source_refs.extend(doc_refs[:4])

        source_refs = list(dict.fromkeys(source_refs))[:_MAX_SOURCES]
        principles_cn = self._synthesize_principles(findings)
        risks_cn = self._synthesize_risks(findings)

        total_findings = sum(len(v) for v in findings.values())
        summary_cn = (
            f"研究完成：从 {len(source_refs)} 个来源查询到 {total_findings} 条相关记录。"
            f"核心原则：{'; '.join(principles_cn[:3]) if principles_cn else '基于查询结果分析'}。"
            f"风险识别：{'; '.join(risks_cn[:3]) if risks_cn else '未发现重大风险'}。"
        )

        return self._service.produce_summary(
            brief_id=brief_id,
            summary_cn=summary_cn,
            principles_cn=principles_cn,
            risks_cn=risks_cn,
            source_refs=source_refs,
        )

    def _extract_keywords(self, text: str) -> list[str]:
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "怎么", "什么", "如何", "可以", "能", "让", "为", "与", "及", "或"}
        words = []
        current = ""
        for ch in text:
            if ch.isalnum() or ch == "_":
                current += ch
            else:
                if current and current not in stop_words and len(current) > 1:
                    words.append(current)
                current = ""
        if current and current not in stop_words and len(current) > 1:
            words.append(current)
        return words[:10] if words else ["research"]

    def _synthesize_principles(self, findings: dict[str, list]) -> list[str]:
        principles = []
        if "code_map" in findings:
            principles.append("代码结构遵循现有架构模式")
        if "decision_memory" in findings:
            principles.append("遵循项目历史决策约定")
        if "failure_memory" in findings:
            principles.append("规避已知失败模式")
        if "project_docs" in findings:
            principles.append("对齐项目文档规范")
        return principles

    def _synthesize_risks(self, findings: dict[str, list]) -> list[str]:
        risks = []
        risk_keywords = {
            "permission": "权限绕过风险",
            "approve_permission": "自动审批风险",
            "shell": "shell 注入风险",
            "subprocess": "子进程执行风险",
            "exec": "动态执行风险",
            "eval": "eval 注入风险",
            "ipcRenderer": "renderer 暴露风险",
            "process": "process 暴露风险",
            "push": "自动 push 风险",
            "release": "自动 release 风险",
            "delete": "自动 delete 风险",
            "tag": "自动 tag 风险",
        }
        for category, items in findings.items():
            for item in items:
                item_str = ""
                if isinstance(item, dict):
                    item_str = json.dumps(item, ensure_ascii=False).lower()
                else:
                    for attr in ("category", "milestone", "path", "reason", "error"):
                        val = getattr(item, attr, None)
                        if val:
                            item_str += str(val).lower() + " "
                for kw, risk_cn in risk_keywords.items():
                    if kw in item_str and risk_cn not in risks:
                        risks.append(risk_cn)
        return risks[:5]

    def _read_project_docs(self, keywords: list[str]) -> list[str]:
        if not self._docs_dir or not self._docs_dir.exists():
            return []
        refs = []
        for doc_file in sorted(self._docs_dir.glob("**/*.md")):
            if doc_file.name in {"README.md", "CHANGELOG.md"}:
                continue
            try:
                content = doc_file.read_text(encoding="utf-8")
                for kw in keywords:
                    if kw.lower() in content.lower():
                        rel = doc_file.relative_to(self._docs_dir.parent)
                        refs.append(str(rel))
                        break
            except (OSError, UnicodeDecodeError):
                continue
        return refs[:4]
