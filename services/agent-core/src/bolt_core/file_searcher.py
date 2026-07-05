import os
from dataclasses import dataclass, field
from pathlib import Path

from bolt_core.path_guard import PathGuard

EXCLUDED_DIRS = {"node_modules", ".git", "dist", ".venv", "__pycache__", ".pytest_cache"}
MAX_MATCHES = 50
MAX_CONTENT_LINE_BYTES = 4 * 1024


@dataclass(frozen=True)
class SearchHit:
    path: str
    line: int | None
    snippet: str


@dataclass(frozen=True)
class FileSearchOutcome:
    status: str
    query: str
    hits: list[SearchHit] = field(default_factory=list)
    error: str | None = None


def search_workspace_files(workspace: str, query: str, mode: str = "name") -> FileSearchOutcome:
    if not query:
        return FileSearchOutcome("failed", query, [], "empty query")
    root = Path(workspace).resolve()
    if not root.is_dir():
        return FileSearchOutcome("failed", query, [], "workspace is not a directory")
    hits = _collect_hits(root, query, mode)
    return FileSearchOutcome("executed", query, hits, None)


def _collect_hits(root: Path, query: str, mode: str) -> list[SearchHit]:
    guard = PathGuard(str(root))
    needle = query.lower()
    hits: list[SearchHit] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        hits.extend(_scan_filenames(dirpath, filenames, needle, guard, mode))
        if mode in ("content", "both"):
            hits.extend(_scan_contents(dirpath, filenames, needle, guard))
        if len(hits) >= MAX_MATCHES:
            return hits[:MAX_MATCHES]
    return hits[:MAX_MATCHES]


def _scan_filenames(dirpath, filenames, needle, guard, mode) -> list[SearchHit]:
    if mode not in ("name", "both"):
        return []
    found: list[SearchHit] = []
    for name in filenames:
        if needle not in name.lower():
            continue
        full = os.path.join(dirpath, name)
        if not guard.check(full).allowed:
            continue
        found.append(SearchHit(full, None, name))
    return found


def _scan_contents(dirpath, filenames, needle, guard) -> list[SearchHit]:
    found: list[SearchHit] = []
    for name in filenames:
        full = os.path.join(dirpath, name)
        check = guard.check(full)
        if not check.allowed:
            continue
        found.extend(_match_lines(full, check.path, needle))
    return found


def _match_lines(original, path: Path, needle: str) -> list[SearchHit]:
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if len(data) > MAX_CONTENT_LINE_BYTES * 64:
        return []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    hits: list[SearchHit] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line.lower():
            hits.append(SearchHit(original, index, line.strip()[:MAX_CONTENT_LINE_BYTES]))
    return hits
