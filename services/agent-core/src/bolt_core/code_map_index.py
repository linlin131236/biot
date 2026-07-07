"""Code Map Index. Minimal file-level index for agent context awareness.

Read-only. Uses static text parsing, never imports project modules.
Excludes: node_modules, dist, build, cache, venv, .bolt, secrets, certs.

Index scope limited to:
- services/agent-core/src/bolt_core
- services/agent-core/tests
- apps/desktop/src
- packages/shared/src
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Excluded paths ────────────────────────────────────────────────────
_EXCLUDED_PARTS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv",
    "venv", ".bolt", "uv.lock",
}
_EXCLUDED_FILES = {
    ".env", ".env.local", "credentials.json", "secrets", "cert.pem",
    "private.key", "id_rsa",
}

# ── Category mapping ──────────────────────────────────────────────────
_CATEGORY_RULES: list[tuple[str, str]] = [
    ("tests/", "test"),
    ("test_", "test"),
    ("apps/desktop/src", "frontend"),
    ("packages/shared/src", "shared"),
    ("/bolt_core/", "service"),
    ("docs/", "docs"),
]


def _classify_category(file_path: str) -> str:
    """Classify file into category based on path."""
    lower = file_path.lower().replace("\\", "/")
    for pattern, category in _CATEGORY_RULES:
        if pattern in lower:
            return category
    if lower.endswith(".py"):
        return "service" if "src/" in lower else "unknown"
    if lower.endswith((".ts", ".tsx")):
        return "frontend"
    if lower.endswith((".md", ".txt")):
        return "docs"
    return "unknown"


@dataclass(frozen=True)
class CodeMapEntry:
    """Single file entry in the code map."""
    file_path: str
    module: str
    category: str
    symbols: list[str]
    role_summary: str  # 中文一句话
    risk_hints: list[str]
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "module": self.module,
            "category": self.category,
            "symbols": self.symbols,
            "role_summary": self.role_summary,
            "risk_hints": self.risk_hints,
            "source_refs": self.source_refs,
        }


class CodeMapIndexService:
    """Minimal read-only code map index. Static parsing, no imports."""

    _RISK_KEYWORDS = [
        "permission", "permissiongate", "approve_permission",
        "shell", "subprocess", "os.system", "exec", "eval",
        "file.write", "file.patch", "ipcRenderer", "process.",
        "push", "release", "tag", "delete",
    ]

    def __init__(self, workspace: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace).resolve())
        self._index: dict[str, CodeMapEntry] = {}
        self._scope_dirs = [
            self._workspace / "services/agent-core/src/bolt_core",
            self._workspace / "services/agent-core/tests",
            self._workspace / "apps/desktop/src",
            self._workspace / "packages/shared/src",
        ]

    @staticmethod
    def _find_project_root(start: Path) -> Path:
        """Walk up to find project root (has package.json + services/ dir)."""
        current = start
        for _ in range(5):
            # Monorepo root: has package.json AND services/ subdirectory
            if (current / "package.json").exists() and (current / "services").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return start  # fallback

    def build_index(self) -> int:
        """Build the code map index. Returns count of indexed files."""
        self._index.clear()
        for scope_dir in self._scope_dirs:
            if not scope_dir.exists():
                continue
            for file_path in scope_dir.rglob("*"):
                if not self._is_indexable(file_path):
                    continue
                entry = self._index_file(file_path)
                if entry is not None:
                    self._index[str(file_path.relative_to(self._workspace))] = entry
        return len(self._index)

    def list_entries(self, category: str | None = None) -> list[dict]:
        """List all indexed entries, optionally filtered by category."""
        if not self._index:
            self.build_index()
        entries = self._index.values()
        if category:
            entries = [e for e in entries if e.category == category]
        return [e.to_dict() for e in sorted(entries, key=lambda e: e.file_path)]

    def query(self, keyword: str) -> list[dict]:
        """Query entries by keyword match on path, symbols, or summary."""
        if not self._index:
            self.build_index()
        kw = keyword.lower()
        results: list[CodeMapEntry] = []
        for entry in self._index.values():
            text = f"{entry.file_path} {' '.join(entry.symbols)} {entry.role_summary}".lower()
            if kw in text:
                results.append(entry)
        return [e.to_dict() for e in sorted(results, key=lambda e: e.file_path)]

    def get_file_summary(self, file_path: str) -> dict | None:
        """Get a single file's code map summary."""
        if not self._index:
            self.build_index()
        # Normalize path
        normalized = file_path.replace("\\", "/")
        for key, entry in self._index.items():
            if key.replace("\\", "/") == normalized:
                return entry.to_dict()
        # Try partial match
        for key, entry in self._index.items():
            if key.replace("\\", "/").endswith(normalized):
                return entry.to_dict()
        return None

    def summary(self) -> dict:
        """Return a summary of the index."""
        if not self._index:
            self.build_index()
        cats: dict[str, int] = {}
        risk_count = 0
        for entry in self._index.values():
            cats[entry.category] = cats.get(entry.category, 0) + 1
            if entry.risk_hints:
                risk_count += 1
        return {
            "total_files": len(self._index),
            "by_category": cats,
            "files_with_risk_hints": risk_count,
            "scope": [str(d.relative_to(self._workspace)) for d in self._scope_dirs if d.exists()],
        }

    # ── Internal helpers ──────────────────────────────────────────────

    def _is_indexable(self, path: Path) -> bool:
        if not path.is_file():
            return False
        parts = set(path.parts)
        if parts & _EXCLUDED_PARTS:
            return False
        if path.name in _EXCLUDED_FILES or path.name.startswith(".env"):
            return False
        if path.suffix not in (".py", ".ts", ".tsx", ".js"):
            return False
        if path.stat().st_size > 500_000:  # skip files > 500KB
            return False
        return True

    def _index_file(self, file_path: Path) -> CodeMapEntry | None:
        """Index a single file. Returns None if unreadable."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        rel_path = str(file_path.relative_to(self._workspace)).replace("\\", "/")
        module = rel_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] if "/" in rel_path else rel_path
        category = _classify_category(rel_path)

        # Extract symbols
        symbols: list[str] = []
        if file_path.suffix == ".py":
            symbols = self._extract_python_symbols(content)
        elif file_path.suffix in (".ts", ".tsx"):
            symbols = self._extract_ts_symbols(content)

        # Role summary (Chinese, one line)
        role_summary = self._extract_role_summary(content, file_path.suffix)

        # Risk hints
        risk_hints = self._detect_risks(rel_path, content)

        return CodeMapEntry(
            file_path=rel_path,
            module=module,
            category=category,
            symbols=symbols[:30],  # limit
            role_summary=role_summary,
            risk_hints=risk_hints,
            source_refs=[f"fs:{rel_path}"],
        )

    def _extract_python_symbols(self, content: str) -> list[str]:
        """Extract class/function names from Python source."""
        symbols: list[str] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class:{node.name}")
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("_"):
                        symbols.append(f"def:{node.name}")
                elif isinstance(node, ast.AsyncFunctionDef):
                    if not node.name.startswith("_"):
                        symbols.append(f"async def:{node.name}")
        except SyntaxError:
            pass
        return symbols

    def _extract_ts_symbols(self, content: str) -> list[str]:
        """Extract exports and function names from TS source (regex-based)."""
        symbols: list[str] = []
        for match in re.finditer(
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content
        ):
            symbols.append(f"function:{match.group(1)}")
        for match in re.finditer(
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)', content
        ):
            symbols.append(f"var:{match.group(1)}")
        for match in re.finditer(r'export\s+(?:interface|type)\s+(\w+)', content):
            symbols.append(f"type:{match.group(1)}")
        return symbols

    def _extract_role_summary(self, content: str, suffix: str) -> str:
        """Extract a Chinese one-line role summary from docstring or first comment."""
        if suffix == ".py":
            # Try module docstring
            match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if match:
                first_line = match.group(1).strip().split("\n")[0].strip()
                if first_line and any('\u4e00' <= c <= '\u9fff' for c in first_line):
                    return first_line[:100]
        # Try first line comment
        for line in content.split("\n")[:5]:
            line = line.lstrip("# ").strip()
            if line and any('\u4e00' <= c <= '\u9fff' for c in line):
                return line[:100]
        # Fallback
        return f"{suffix.lstrip('.')} 文件"

    def _detect_risks(self, rel_path: str, content: str) -> list[str]:
        """Detect risk hints based on keywords."""
        hints: list[str] = []
        lower_content = content.lower()
        for kw in self._RISK_KEYWORDS:
            if kw.lower() in lower_content:
                hints.append(kw)
        return list(set(hints))  # deduplicate
