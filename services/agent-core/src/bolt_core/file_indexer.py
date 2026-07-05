from __future__ import annotations

import os
import re
from pathlib import Path

from bolt_core.file_searcher import EXCLUDED_DIRS
from bolt_core.path_guard import PathGuard
from bolt_core.perception_types import FileIndex, FileIndexEntry

INDEX_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"}
MAX_FILES = 120
MAX_FILE_BYTES = 64 * 1024
MAX_ENTRIES = 80

PY_IMPORT = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")
PY_SYMBOL = re.compile(r"^(?:class|def)\s+(\w+)")
JS_IMPORT = re.compile(r"(?:import|export)\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")
JS_EXPORT = re.compile(r"^export\s+(?:async\s+)?(?:function|class|const|let|var|interface|type)\s+(\w+)")
JS_SYMBOL = re.compile(r"^(?:class|function)\s+(\w+)")


def index_workspace_files(workspace: str, max_files: int = MAX_FILES, max_entries: int = MAX_ENTRIES) -> FileIndex:
    root = Path(workspace).resolve()
    guard = PathGuard(str(root))
    entries: list[FileIndexEntry] = []
    skipped: dict[str, int] = {}
    truncated = False
    seen = 0
    for path in _walk(root):
        if len(entries) >= max_entries or seen >= max_files:
            truncated = True
            break
        outcome = _index_path(path, guard, skipped)
        if outcome is None:
            continue
        seen += 1
        entries.append(outcome)
    return FileIndex(entries, skipped, truncated)


def _walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def _index_path(path: Path, guard: PathGuard, skipped: dict[str, int]) -> FileIndexEntry | None:
    check = guard.check(str(path))
    if not check.allowed:
        _count(skipped, _skip_key(check.reason))
        return None
    if path.suffix.lower() not in INDEX_SUFFIXES:
        _count(skipped, "unsupported_extension")
        return None
    text = _read_text(path, skipped)
    if text is None:
        return None
    imports, exports, symbols = _extract(text, path.suffix.lower())
    return FileIndexEntry(str(path), imports, exports, symbols)


def _read_text(path: Path, skipped: dict[str, int]) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            _count(skipped, "too_large")
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        _count(skipped, "decode_error")
    except OSError:
        _count(skipped, "read_error")
    return None


def _extract(text: str, suffix: str) -> tuple[list[str], list[str], list[str]]:
    if suffix == ".py":
        return _extract_python(text)
    if suffix in {".ts", ".tsx", ".js", ".jsx"}:
        return _extract_js(text)
    return [], [], []


def _extract_python(text: str) -> tuple[list[str], list[str], list[str]]:
    imports: list[str] = []
    symbols: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        import_match = PY_IMPORT.match(stripped)
        symbol_match = PY_SYMBOL.match(stripped)
        if import_match:
            imports.append((import_match.group(1) or import_match.group(2)).split(".")[0])
        if symbol_match:
            symbols.append(symbol_match.group(1))
    return _unique(imports), [], _unique(symbols)


def _extract_js(text: str) -> tuple[list[str], list[str], list[str]]:
    imports: list[str] = []
    exports: list[str] = []
    symbols: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        imports.extend(JS_IMPORT.findall(stripped))
        _append_match(exports, JS_EXPORT.match(stripped))
        _append_match(symbols, JS_SYMBOL.match(stripped))
    return _unique(imports), _unique(exports), _unique(symbols + exports)


def _append_match(values: list[str], match) -> None:
    if match:
        values.append(match.group(1))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _skip_key(reason: str) -> str:
    if reason == "secret path denied":
        return "secret_path"
    return reason.replace(" ", "_")


def _count(skipped: dict[str, int], key: str) -> None:
    skipped[key] = skipped.get(key, 0) + 1
