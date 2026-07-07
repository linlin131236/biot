"""Failure Memory Index Service. Read-only index of historical failures.

Sources: review gates, project-state, existing FailureStore.
Aligns with M64 FailureClassifier (8 categories) and M65 SafeRetryLoop.
Never auto-fixes, never auto-retries dangerous tools.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class FailureRecord:
    """A single historical failure with Chinese explanation."""
    failure_id: str
    category: str
    severity: str
    milestone: str
    symptom_cn: str
    root_cause_cn: str
    fix_summary_cn: str
    verification: str
    recurrence_risk: str
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "failure_id": self.failure_id,
            "category": self.category,
            "severity": self.severity,
            "milestone": self.milestone,
            "symptom_cn": self.symptom_cn,
            "root_cause_cn": self.root_cause_cn,
            "fix_summary_cn": self.fix_summary_cn,
            "verification": self.verification,
            "recurrence_risk": self.recurrence_risk,
            "source_refs": self.source_refs,
        }


# ── Category alignment with M64 FailureClassifier ──────────────────────
_M64_CATEGORIES = {
    "user_input": "用户输入问题",
    "permission_waiting": "权限等待",
    "tool_failure": "工具执行失败",
    "test_failure": "测试失败",
    "network_failure": "网络失败",
    "code_quality": "代码质量失败",
    "security_block": "安全阻断",
    "unknown": "未知失败",
}

# ── Excluded paths ─────────────────────────────────────────────────────
_EXCLUDED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv",
    "venv", ".bolt", "uv.lock",
}
_EXCLUDED_FILES = {
    ".env", ".env.local", "credentials.json", "secrets", "cert.pem",
    "private.key", "id_rsa", ".npmrc",
}


def _is_safe_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & _EXCLUDED_DIRS:
        return False
    if path.name in _EXCLUDED_FILES or path.name.startswith(".env"):
        return False
    return True


class FailureMemoryIndexService:
    """Read-only index of project failure history.

    Builds from review gates, project-state, and existing FailureStore.
    Categories aligned with M64 FailureClassifier.
    NEVER auto-fixes, auto-retries, or auto-approves.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace_path).resolve())
        self._docs_dir = self._workspace / "docs"
        self._records: Optional[list[FailureRecord]] = None

    @staticmethod
    def _find_project_root(start: Path) -> Path:
        current = start
        for _ in range(5):
            if (current / "package.json").exists() and (current / "services").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return start

    # ── Public API ─────────────────────────────────────────────────────

    def list_all(self) -> list[FailureRecord]:
        self._ensure_indexed()
        return list(self._records or [])

    def get_detail(self, failure_id: str) -> Optional[FailureRecord]:
        self._ensure_indexed()
        for r in (self._records or []):
            if r.failure_id == failure_id:
                return r
        return None

    def query_by_category(self, category: str) -> list[FailureRecord]:
        self._ensure_indexed()
        cat_lower = category.lower()
        results: list[FailureRecord] = []
        for r in (self._records or []):
            if cat_lower in r.category.lower():
                results.append(r)
        return results

    def query_by_keyword(self, keyword: str) -> list[FailureRecord]:
        self._ensure_indexed()
        kw = keyword.lower()
        results: list[FailureRecord] = []
        for r in (self._records or []):
            searchable = (
                r.symptom_cn + r.root_cause_cn + r.fix_summary_cn +
                r.category + r.verification
            ).lower()
            if kw in searchable:
                results.append(r)
        return results

    # ── Indexing ───────────────────────────────────────────────────────

    def _ensure_indexed(self) -> None:
        if self._records is not None:
            return
        self._records = self._index_all()

    def _index_all(self) -> list[FailureRecord]:
        records: list[FailureRecord] = []

        # Source 1: Review gates (P1/P2 fix records)
        records.extend(self._from_review_gates())

        # Source 2: Project state (known risks)
        records.extend(self._from_project_state())

        return records

    # ── Source: Review Gates ────────────────────────────────────────────

    def _from_review_gates(self) -> list[FailureRecord]:
        """Extract P1/P2 fix records from phase review gates."""
        records: list[FailureRecord] = []
        gates_dir = self._docs_dir

        for fpath in sorted(gates_dir.glob("phase-*-review-gate.md")):
            if not _is_safe_path(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            records.extend(self._parse_review_gate(fpath, content))

        return records

    def _parse_review_gate(self, fpath: Path, content: str) -> list[FailureRecord]:
        """Parse a single review gate for P1/P2 fix records."""
        records: list[FailureRecord] = []
        milestone = self._extract_milestone_from_path(fpath)
        rel_path = f"docs/{fpath.name}"

        # Look for P1/P2 fix entries
        lines = content.split("\n")
        in_fix = False
        current_severity = ""
        fix_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Detect P1/P2 fix lines
            if re.search(r'\bP[12]\b.*修复|修复.*\bP[12]\b|fix.*\bP[12]\b|\bP[12]\b.*fix', stripped, re.IGNORECASE):
                if in_fix and fix_lines:
                    records.append(self._build_failure_record(
                        milestone, current_severity, fix_lines, rel_path, fpath.stem
                    ))
                in_fix = True
                current_severity = "P1" if "P1" in stripped.upper() else "P2"
                fix_lines = [stripped]
                continue

            if in_fix:
                if stripped.startswith("##") or stripped.startswith("# "):
                    if fix_lines:
                        records.append(self._build_failure_record(
                            milestone, current_severity, fix_lines, rel_path, fpath.stem
                        ))
                    in_fix = False
                    fix_lines = []
                elif stripped:
                    fix_lines.append(stripped)

        # Handle last entry
        if in_fix and fix_lines:
            records.append(self._build_failure_record(
                milestone, current_severity, fix_lines, rel_path, fpath.stem
            ))

        return records

    def _build_failure_record(
        self, milestone: str, severity: str,
        lines: list[str], rel_path: str, stem: str,
    ) -> FailureRecord:
        """Build a FailureRecord from extracted fix lines."""
        full_text = " ".join(lines)

        # Determine category from content
        category = self._infer_category(full_text)

        # Split into symptom / root cause / fix / verification
        symptom_cn = self._extract_symptom(full_text, lines)
        root_cause_cn = self._extract_root_cause(full_text)
        fix_summary_cn = self._extract_fix_summary(full_text)
        verification = self._extract_verification(full_text)
        recurrence_risk = self._assess_recurrence_risk(category, severity, full_text)

        return FailureRecord(
            failure_id=f"{stem}-{severity.lower()}",
            category=category,
            severity=severity,
            milestone=milestone,
            symptom_cn=symptom_cn,
            root_cause_cn=root_cause_cn,
            fix_summary_cn=fix_summary_cn,
            verification=verification,
            recurrence_risk=recurrence_risk,
            source_refs=[rel_path],
        )

    # ── Source: Project State ──────────────────────────────────────────

    def _from_project_state(self) -> list[FailureRecord]:
        """Extract known risks from project-state.md."""
        ps_path = self._docs_dir / "project-state.md"
        if not ps_path.exists() or not _is_safe_path(ps_path):
            return []

        try:
            content = ps_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []

        records: list[FailureRecord] = []
        rel_path = "docs/project-state.md"

        # Extract from "已知风险" and "当前风险" sections
        in_risks = False
        risk_lines: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            if "已知风险" in stripped or "当前风险" in stripped:
                in_risks = True
                continue
            if in_risks:
                if stripped.startswith("##") or stripped.startswith("# "):
                    break
                if stripped.startswith("- "):
                    risk_lines.append(stripped.lstrip("- "))

        for i, risk_text in enumerate(risk_lines):
            if len(risk_text) < 10:
                continue
            records.append(FailureRecord(
                failure_id=f"risk-ps-{i + 1}",
                category="unknown",
                severity="P3",
                milestone="项目级",
                symptom_cn=risk_text[:200],
                root_cause_cn="项目状态文档中记录的已知风险",
                fix_summary_cn="待评估和修复",
                verification="需在后续 milestone 中处理",
                recurrence_risk="中",
                source_refs=[rel_path],
            ))

        return records

    # ── Parsing helpers ────────────────────────────────────────────────

    @staticmethod
    def _extract_milestone_from_path(fpath: Path) -> str:
        match = re.search(r'phase-(\d+)', fpath.name)
        if match:
            return f"M{match.group(1)}"
        return "未知"

    @staticmethod
    def _infer_category(text: str) -> str:
        """Infer M64-aligned category from fix description."""
        lower = text.lower()
        if any(kw in lower for kw in ["test", "测试", "pytest", "assert"]):
            return "test_failure"
        if any(kw in lower for kw in ["安全", "secret", "token", "permission", "权限"]):
            return "security_block"
        if any(kw in lower for kw in ["build", "编译", "类型", "type", "lint"]):
            return "code_quality"
        if any(kw in lower for kw in ["whitespace", "格式", "trailing", "diff"]):
            return "code_quality"
        if any(kw in lower for kw in ["类型", "interface", "protocol", "结构"]):
            return "code_quality"
        return "unknown"

    @staticmethod
    def _extract_symptom(text: str, lines: list[str]) -> str:
        """Extract symptom from fix description."""
        # First line often describes the symptom
        if lines:
            first = lines[0]
            # Remove leading markers
            first = re.sub(r'^[-*]\s+', '', first)
            first = re.sub(r'^P[12]\s*[:：]?\s*', '', first)
            if len(first) > 200:
                first = first[:197] + "..."
            return first if len(first) > 10 else "未明确描述症状"
        return "未明确描述症状"

    @staticmethod
    def _extract_root_cause(text: str) -> str:
        """Extract root cause from fix description."""
        cause_matches = re.findall(
            r'(?:原因|根因|root.?cause|因为|由于|问题在于)[：:]\s*(.+?)(?:[。；;]|$)',
            text, re.IGNORECASE,
        )
        if cause_matches:
            result = cause_matches[0].strip()
            if len(result) > 200:
                result = result[:197] + "..."
            return result
        return "从修复描述中推断（未记录明确根因）"

    @staticmethod
    def _extract_fix_summary(text: str) -> str:
        """Extract fix summary."""
        fix_matches = re.findall(
            r'(?:修复|fix|解决)[：:]\s*(.+?)(?:[。；;]|$)',
            text, re.IGNORECASE,
        )
        if fix_matches:
            result = fix_matches[0].strip()
            if len(result) > 200:
                result = result[:197] + "..."
            return result

        # Fallback: use the whole text as fix summary
        cleaned = re.sub(r'^[-*]\s+', '', text)
        cleaned = re.sub(r'^P[12]\s*[:：]?\s*', '', cleaned)
        if len(cleaned) > 200:
            cleaned = cleaned[:197] + "..."
        return cleaned if len(cleaned) > 5 else "未记录修复摘要"

    @staticmethod
    def _extract_verification(text: str) -> str:
        """Extract verification method."""
        verify_matches = re.findall(
            r'(?:验证|verify|test|测试)[：:]\s*(.+?)(?:[。；;]|$)',
            text, re.IGNORECASE,
        )
        if verify_matches:
            return verify_matches[0].strip()[:200]

        if "pytest" in text.lower() or "test" in text.lower():
            return "通过 targeted tests 验证"
        if "git diff" in text.lower():
            return "通过 git diff --check 验证"
        return "通过 review gate 复审验证"

    @staticmethod
    def _assess_recurrence_risk(category: str, severity: str, text: str) -> str:
        """Assess recurrence risk based on category and severity."""
        lower = text.lower()

        # High risk indicators
        if any(kw in lower for kw in ["whitespace", "trailing", "格式", "换行"]):
            return "高（格式问题易复发，需 lint 自动化）"
        if any(kw in lower for kw in ["类型", "type", "interface", "protocol"]):
            return "中（类型/协议不一致在新功能中可能重现）"

        # Category-based assessment
        if category == "security_block":
            return "低（安全阻断修复后不易复发，除非引入新危险路径）"
        if category == "test_failure":
            return "中（测试失败频率取决于测试覆盖率和代码变更量）"
        if category == "code_quality":
            return "中（代码质量问题在快速迭代中容易重现）"

        # Severity-based
        if severity == "P1":
            return "低（P1 修复通常彻底，不易复发）"
        if severity == "P2":
            return "中（P2 修复可能遗留边缘情况）"

        return "未知"
