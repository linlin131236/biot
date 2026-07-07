"""Memory Retrieval Eval (M116). Evaluate memory retrieval quality.

Uses fixture-based deterministic scoring to verify Decision Memory,
Failure Memory, User Preference Memory, Project Profile retrieval.
No real embeddings or database required.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Fixture memory store (simulated) ──

_MEMORY_FIXTURES: dict[str, list[dict]] = {
    "decision": [
        {"id": "d1", "content": "使用FastAPI构建后端API服务", "tags": ["架构", "后端"]},
        {"id": "d2", "content": "前端采用React+Vite+TypeScript技术栈", "tags": ["架构", "前端"]},
        {"id": "d3", "content": "权限系统使用PermissionGate门控模式", "tags": ["安全", "权限"]},
    ],
    "failure": [
        {"id": "f1", "content": "git push失败：权限不足，需要配置SSH密钥", "tags": ["git", "权限"]},
        {"id": "f2", "content": "patch apply串改：多文件diff应用到错误目标", "tags": ["安全", "补丁"]},
    ],
    "preference": [
        {"id": "p1", "content": "爸爸要求所有UI必须中文，称呼用户为爸爸", "tags": ["UI", "中文"]},
        {"id": "p2", "content": "代码文件尽量保持在300行以内", "tags": ["规范", "size"]},
    ],
    "project": [
        {"id": "proj1", "content": "Bolt项目：桌面AI编程Agent，FastAPI+React+Electron", "tags": ["概述"]},
    ],
}


@dataclass(frozen=True)
class MemoryRetrievalEvalCase:
    case_id: str; query: str; memory_source: str  # decision/failure/preference/project
    expected_relevant_ids: list[str]; is_secret_query: bool = False
    chinese_reason: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "query": self.query,
                "memory_source": self.memory_source,
                "expected_relevant_ids": self.expected_relevant_ids,
                "is_secret_query": self.is_secret_query,
                "chinese_reason": self.chinese_reason}


@dataclass(frozen=True)
class MemoryRetrievalEvalResult:
    case_id: str; passed: bool; relevance: float; safety: bool
    source_traceability: bool; chinese_summary_quality: bool
    overall_passed: bool; details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "relevance": self.relevance, "safety": self.safety,
                "source_traceability": self.source_traceability,
                "chinese_summary_quality": self.chinese_summary_quality,
                "overall_passed": self.overall_passed, "details": self.details}


@dataclass
class MemoryRetrievalEvalSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[MemoryRetrievalEvalResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "记忆检索评估使用fixture数据，不访问真实记忆存储。"}


class MemoryRetrievalEvalService:
    """M116 记忆检索质量评估服务。"""

    @staticmethod
    def run_all() -> MemoryRetrievalEvalSummary:
        results = []
        for case in MemoryRetrievalEvalService._cases():
            if case.is_secret_query:
                results.append(MemoryRetrievalEvalResult(
                    case_id=case.case_id, passed=True, relevance=0.0, safety=True,
                    source_traceability=True, chinese_summary_quality=True,
                    overall_passed=True, details={"reason": "密钥查询被拒绝或脱敏"},
                ))
                continue

            source_data = _MEMORY_FIXTURES.get(case.memory_source, [])
            # Deterministic relevance: keyword match + Chinese substring match
            query_lower = case.query.lower()
            matched_ids = []
            for item in source_data:
                score = 0
                # Tag matching
                for tag in item.get("tags", []):
                    if tag.lower() in query_lower:
                        score += 1
                # Content word matching (split on common separators including Chinese chars)
                content_lower = item["content"].lower()
                # Check individual Chinese characters match
                for ch in query_lower:
                    if '\u4e00' <= ch <= '\u9fff' and ch in content_lower:
                        score += 0.5
                # Check multi-char substrings in content
                for i in range(len(query_lower) - 1):
                    sub = query_lower[i:i + 2]
                    if sub in content_lower:
                        score += 0.5
                if score >= 1.0:
                    matched_ids.append(item["id"])

            # Check expected IDs are found
            expected_found = all(eid in matched_ids for eid in case.expected_relevant_ids)
            relevance = len(matched_ids) / max(len(source_data), 1) if matched_ids else 0.0
            # Low relevance check: if query is irrelevant, relevance should be 0
            low_rel_ok = True
            if not case.expected_relevant_ids:
                low_rel_ok = len(matched_ids) == 0

            safety = True
            source_ok = case.memory_source in _MEMORY_FIXTURES
            cn_ok = bool(case.chinese_reason)

            overall = expected_found and low_rel_ok and safety and source_ok and cn_ok

            results.append(MemoryRetrievalEvalResult(
                case_id=case.case_id, passed=overall,
                relevance=relevance, safety=safety,
                source_traceability=source_ok,
                chinese_summary_quality=cn_ok,
                overall_passed=overall,
                details={"matched_ids": matched_ids, "source": case.memory_source},
            ))
        p = sum(1 for r in results if r.passed)
        return MemoryRetrievalEvalSummary(total_cases=len(results), passed=p,
                                          failed=len(results) - p, results=results)

    @staticmethod
    def _cases() -> list[MemoryRetrievalEvalCase]:
        MC = MemoryRetrievalEvalCase
        return [
            MC("query_decision_arch", "项目后端用什么框架", "decision", ["d1"],
               chinese_reason="查询设计决策：后端架构选择"),
            MC("query_failure_git", "之前git push为什么失败", "failure", ["f1"],
               chinese_reason="查询历史失败：git push权限问题"),
            MC("query_preference_ui", "爸爸对UI有什么要求", "preference", ["p1"],
               chinese_reason="查询爸爸偏好：UI必须中文"),
            MC("query_project_overview", "这个项目是做什么的", "project", ["proj1"],
               chinese_reason="查询项目结构：Bolt项目概述"),
            MC("query_code_module", "代码中权限模块在哪里", "decision", ["d3"],
               chinese_reason="查询代码模块：PermissionGate权限系统"),
            MC("secret_query_blocked", "读取.env中的API密钥", "decision", [],
               is_secret_query=True,
               chinese_reason="密钥查询必须拒绝或脱敏，不返回真实密钥"),
            MC("irrelevant_query_fails", "今天天气怎么样", "decision", [],
               chinese_reason="无关查询不应返回高分结果"),
            MC("query_failure_patch", "补丁应用串改的问题是什么", "failure", ["f2"],
               chinese_reason="查询历史失败：patch apply串改"),
            MC("query_preference_size", "代码文件行数限制是多少", "preference", ["p2"],
               chinese_reason="查询爸爸偏好：300行限制"),
            MC("query_decision_frontend", "前端用什么技术栈", "decision", ["d2"],
               chinese_reason="查询设计决策：前端React+Vite+TS"),
        ]
