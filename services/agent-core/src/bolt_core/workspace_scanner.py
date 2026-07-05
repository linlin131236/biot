from __future__ import annotations

import json
import os
from pathlib import Path

from bolt_core.file_searcher import EXCLUDED_DIRS
from bolt_core.path_guard import PathGuard
from bolt_core.perception_types import WorkspaceProfile

MAX_SCAN_FILES = 200
MANIFEST_NAMES = {"package.json", "pyproject.toml", "requirements.txt", "pnpm-lock.yaml", "package-lock.json", "yarn.lock"}
ENTRY_NAMES = {"main.ts", "main.tsx", "main.js", "main.jsx", "App.tsx", "App.ts", "app.py", "main.py"}


def scan_workspace(workspace: str, max_files: int = MAX_SCAN_FILES) -> WorkspaceProfile:
    root = Path(workspace).resolve()
    guard = PathGuard(str(root))
    skipped: dict[str, int] = {}
    manifests: list[str] = []
    entries: list[str] = []
    languages: set[str] = set()
    truncated = False
    seen = 0
    for path in _walk(root):
        if seen >= max_files:
            truncated = True
            break
        check = guard.check(str(path))
        if not check.allowed:
            _count(skipped, _skip_key(check.reason))
            continue
        seen += 1
        _collect_path(path, manifests, entries, languages)
    package_manager = _package_manager(root, guard, skipped)
    tests, builds = _commands(root, package_manager, guard, skipped)
    return WorkspaceProfile(str(root), root.name, package_manager, sorted(languages), manifests, entries, tests, builds, skipped, truncated)


def _walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def _collect_path(path: Path, manifests: list[str], entries: list[str], languages: set[str]) -> None:
    normalized = _path_text(path)
    if path.name in MANIFEST_NAMES:
        manifests.append(normalized)
    if path.name in ENTRY_NAMES or path.match("src/main.*") or path.match("src/App.*"):
        entries.append(normalized)
    language = _language(path.suffix.lower())
    if language:
        languages.add(language)


def _path_text(path: Path) -> str:
    return str(path).replace("\\", "/")


def _language(suffix: str) -> str | None:
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    if suffix in {".js", ".jsx"}:
        return "javascript"
    if suffix == ".py":
        return "python"
    return None


def _package_manager(root: Path, guard: PathGuard, skipped: dict[str, int]) -> str | None:
    for filename, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")):
        if _safe_exists(root / filename, guard, skipped):
            return manager
    if _safe_exists(root / "package.json", guard, skipped):
        return "npm"
    return None


def _commands(root: Path, manager: str | None, guard: PathGuard, skipped: dict[str, int]) -> tuple[list[str], list[str]]:
    package_json = root / "package.json"
    if not _safe_exists(package_json, guard, skipped):
        return [], []
    scripts = _package_scripts(package_json)
    prefix = manager or "npm"
    tests = [f"{prefix} test"] if "test" in scripts else []
    builds = [f"{prefix} build"] if "build" in scripts else []
    return tests, builds


def _package_scripts(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8")[:8192])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data.get("scripts", {}) if isinstance(data.get("scripts"), dict) else {}


def _safe_exists(path: Path, guard: PathGuard, skipped: dict[str, int]) -> bool:
    check = guard.check(str(path))
    if not check.allowed:
        _count(skipped, _skip_key(check.reason))
        return False
    return path.exists()


def _skip_key(reason: str) -> str:
    if reason == "secret path denied":
        return "secret_path"
    return reason.replace(" ", "_")


def _count(skipped: dict[str, int], key: str) -> None:
    skipped[key] = skipped.get(key, 0) + 1
