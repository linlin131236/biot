"""Decision Memory Service. Builds a read-only index of project design decisions.

Context Lakehouse principles:
- raw/source_refs always preserved
- every conclusion traceable back to docs/decisions/*.md
- NEVER reads secrets or certificate materials
- read-only: does not auto-write new decisions
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DecisionRecord:
    """A single design decision extracted from docs/decisions/."""
    decision_id: str
    milestone: str
    title: str
    summary_cn: str
    rationale: str
    tradeoffs: str
    outcome: str
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "milestone": self.milestone,
            "title": self.title,
            "summary_cn": self.summary_cn,
            "rationale": self.rationale,
            "tradeoffs": self.tradeoffs,
            "outcome": self.outcome,
            "source_refs": self.source_refs,
        }


# ── Excluded paths for safety ─────────────────────────────────────────
_EXCLUDED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv",
    "venv", ".bolt", "uv.lock",
}
_EXCLUDED_FILES = {
    ".env", ".env.local", "credentials.json", "secrets", "cert.pem",
    "private.key", "id_rsa", ".npmrc",
}


def _is_safe_path(path: Path) -> bool:
    """Check if path is safe to read (not excluded)."""
    parts = set(path.parts)
    if parts & _EXCLUDED_DIRS:
        return False
    if path.name in _EXCLUDED_FILES or path.name.startswith(".env"):
        return False
    return True


class DecisionMemoryService:
    """Read-only index of project design decisions from docs/decisions/.

    Parses decision markdown files into structured DecisionRecord objects.
    Supports list, detail, and query-by-milestone/keyword operations.
    NEVER auto-writes new decisions.
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace_path).resolve())
        self._decisions_dir = self._workspace / "docs" / "decisions"
        self._records: Optional[list[DecisionRecord]] = None

    @staticmethod
    def _find_project_root(start: Path) -> Path:
        """Walk up to find project root (has package.json + services/ dir)."""
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

    def list_all(self) -> list[DecisionRecord]:
        """Return all decision records sorted by milestone."""
        self._ensure_indexed()
        return list(self._records or [])

    def get_detail(self, decision_id: str) -> Optional[DecisionRecord]:
        """Get a single decision by ID."""
        self._ensure_indexed()
        for r in (self._records or []):
            if r.decision_id == decision_id:
                return r
        return None

    def query_by_milestone(self, milestone: str) -> list[DecisionRecord]:
        """Query decisions by milestone prefix (e.g. 'M70' returns M70, M70-M72)."""
        self._ensure_indexed()
        milestone_upper = milestone.upper().replace("M", "")
        results: list[DecisionRecord] = []
        for r in (self._records or []):
            if milestone_upper in r.milestone.upper().replace("M", ""):
                results.append(r)
        return sorted(results, key=lambda x: self._sort_key(x.decision_id))

    def query_by_keyword(self, keyword: str) -> list[DecisionRecord]:
        """Query decisions by keyword in title, summary, rationale, or tradeoffs."""
        self._ensure_indexed()
        kw = keyword.lower()
        results: list[DecisionRecord] = []
        for r in (self._records or []):
            searchable = (
                r.title + r.summary_cn + r.rationale + r.tradeoffs + r.outcome
            ).lower()
            if kw in searchable:
                results.append(r)
        return sorted(results, key=lambda x: self._sort_key(x.decision_id))

    @staticmethod
    def _sort_key(decision_id: str) -> tuple:
        """Sort key: numeric prefix first, then rest."""
        match = re.match(r"^(\d+)", decision_id)
        if match:
            return (0, int(match.group(1)), decision_id)
        return (1, 0, decision_id)

    # ── Indexing ───────────────────────────────────────────────────────

    def _ensure_indexed(self) -> None:
        """Lazy index: parse all decision files once."""
        if self._records is not None:
            return
        self._records = self._index_all()

    def _index_all(self) -> list[DecisionRecord]:
        """Parse all .md files in docs/decisions/ and return records."""
        if not self._decisions_dir.exists():
            return []

        records: list[DecisionRecord] = []
        for fpath in sorted(self._decisions_dir.glob("*.md")):
            if not _is_safe_path(fpath):
                continue
            try:
                record = self._parse_file(fpath)
                if record is not None:
                    records.append(record)
            except Exception:
                # Degrade gracefully on any parse error
                records.append(self._degraded_record(fpath))

        return records

    # ── Parser ─────────────────────────────────────────────────────────

    def _parse_file(self, filepath: Path) -> Optional[DecisionRecord]:
        """Parse a single decision markdown file."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return self._degraded_record(filepath)

        if not content.strip():
            return None

        # Decision ID from filename (e.g. "072-code-map-index.md" → "072-code-map-index")
        decision_id = filepath.stem

        # Milestone from filename prefix
        milestone = self._extract_milestone_from_id(decision_id)

        # Title from first H1
        title = self._extract_title(content, decision_id)

        # Summary from first meaningful paragraph after title
        summary_cn = self._extract_summary(content)

        # Rationale from decision/reason sections
        rationale = self._extract_rationale(content)

        # Tradeoffs from risk/drawback sections
        tradeoffs = self._extract_tradeoffs(content)

        # Outcome from decision/conclusion sections
        outcome = self._extract_outcome(content)

        # Source ref
        rel_path = f"docs/decisions/{filepath.name}"
        source_refs = [rel_path]

        return DecisionRecord(
            decision_id=decision_id,
            milestone=milestone,
            title=title,
            summary_cn=summary_cn,
            rationale=rationale,
            tradeoffs=tradeoffs,
            outcome=outcome,
            source_refs=source_refs,
        )

    def _degraded_record(self, filepath: Path) -> DecisionRecord:
        """Return a degraded record when parsing fails."""
        decision_id = filepath.stem
        milestone = self._extract_milestone_from_id(decision_id)
        rel_path = f"docs/decisions/{filepath.name}"
        return DecisionRecord(
            decision_id=decision_id,
            milestone=milestone,
            title=f"解析失败：{filepath.name}",
            summary_cn="此决策文档解析异常，请检查文件格式。",
            rationale="无法解析",
            tradeoffs="无法解析",
            outcome="无法解析",
            source_refs=[rel_path],
        )

    # ── Extraction helpers ─────────────────────────────────────────────

    @staticmethod
    def _extract_milestone_from_id(decision_id: str) -> str:
        """Extract milestone from decision_id prefix, e.g. '072-code-map-index' → 'M72'."""
        match = re.match(r"^(\d+)", decision_id)
        if match:
            num = int(match.group(1))
            return f"M{num}"
        return "未知"

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        """Extract title from first H1 line."""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return fallback

    @staticmethod
    def _extract_summary(content: str) -> str:
        """Extract summary from first meaningful paragraph after title."""
        lines = content.split("\n")
        found_title = False
        paragraphs: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                found_title = True
                continue
            if not found_title:
                continue
            # Skip metadata, headers, empty lines
            if stripped.startswith("##") or stripped.startswith("---"):
                if paragraphs:
                    break
                continue
            if stripped.startswith("**") or stripped.startswith(">") or stripped.startswith("|"):
                continue
            if not stripped:
                if paragraphs:
                    break
                continue
            paragraphs.append(stripped)
            if len(" ".join(paragraphs)) > 200:
                break

        summary = " ".join(paragraphs).strip()
        if not summary:
            return "无法提取摘要"
        # Truncate to ~300 chars max
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary

    @staticmethod
    def _extract_rationale(content: str) -> str:
        """Extract rationale from decision sections (选择/理由/Design Decision/关键设计选择)."""
        rationale_parts: list[str] = []

        # Try to find rationale-rich sections
        in_section = False
        section_buffer: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            lower = stripped.lower()

            # Section headers that indicate rationale
            if re.match(r"^#{1,3}\s+", stripped):
                if in_section and section_buffer:
                    rationale_parts.append(" ".join(section_buffer))
                    section_buffer = []
                in_section = any(kw in lower for kw in [
                    "决策", "设计选择", "design decision", "decisions",
                    "关键设计", "decision", "选择", "理由",
                ])
                if in_section:
                    section_buffer = []
                continue

            if in_section and stripped:
                section_buffer.append(stripped)

        if in_section and section_buffer:
            rationale_parts.append(" ".join(section_buffer))

        if not rationale_parts:
            return "未找到明确理由记录"

        result = " | ".join(rationale_parts[:5])
        if len(result) > 600:
            result = result[:597] + "..."
        return result

    @staticmethod
    def _extract_tradeoffs(content: str) -> str:
        """Extract tradeoffs from risk/drawback/不做的 sections."""
        tradeoff_parts: list[str] = []

        in_section = False
        section_buffer: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            lower = stripped.lower()

            if re.match(r"^#{1,3}\s+", stripped):
                if in_section and section_buffer:
                    tradeoff_parts.append(" ".join(section_buffer))
                    section_buffer = []
                in_section = any(kw in lower for kw in [
                    "风险", "不做", "risk", "tradeoff", "弱点", "weakness",
                    "限制", "limitation", "缺点", "drawback",
                ])
                if in_section:
                    section_buffer = []
                continue

            if in_section and stripped:
                section_buffer.append(stripped)

        if in_section and section_buffer:
            tradeoff_parts.append(" ".join(section_buffer))

        if not tradeoff_parts:
            return "未记录明确风险"

        result = " | ".join(tradeoff_parts[:5])
        if len(result) > 400:
            result = result[:397] + "..."
        return result

    @staticmethod
    def _extract_outcome(content: str) -> str:
        """Extract outcome from conclusion/completed/verification sections."""
        # Look for verification/completion indicators
        outcome_lines: list[str] = []

        in_section = False
        for line in content.split("\n"):
            stripped = line.strip()
            lower = stripped.lower()

            if re.match(r"^#{1,3}\s+", stripped):
                in_section = any(kw in lower for kw in [
                    "验证", "verification", "completed", "完成",
                    "实现", "implemented", "测试", "结果",
                ])
                continue

            if in_section and stripped and not stripped.startswith("```"):
                outcome_lines.append(stripped)
                if len(outcome_lines) >= 8:
                    break

        if outcome_lines:
            result = " ".join(outcome_lines[:8])
            if len(result) > 400:
                result = result[:397] + "..."
            return result

        # Fallback: use the last meaningful paragraph
        paragraphs = content.split("\n\n")
        for para in reversed(paragraphs):
            stripped = para.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                if len(stripped) > 400:
                    stripped = stripped[:397] + "..."
                return stripped

        return "无法确定结果"
