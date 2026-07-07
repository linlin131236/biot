"""Project Profile Service. Builds a structured project portrait for context handoff. Context Lakehouse: raw/source_refs preserved; cleaning reproducible; analysis reads from cleaned layer; conclusions traceable; NEVER reads secrets."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class ProjectProfile:
    """Structured portrait of a Bolt project. Source_refs back every conclusion."""
    project_name: str
    workspace_path: str
    current_milestone: str
    latest_head: str
    origin_state: str
    tech_stack: dict
    key_commands: dict
    hard_rules: list[str]
    important_docs: list[str]
    latest_review_gate: str
    known_risks: list[str]
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "workspace_path": self.workspace_path,
            "current_milestone": self.current_milestone,
            "latest_head": self.latest_head,
            "origin_state": self.origin_state,
            "tech_stack": self.tech_stack,
            "key_commands": self.key_commands,
            "hard_rules": self.hard_rules,
            "important_docs": self.important_docs,
            "latest_review_gate": self.latest_review_gate,
            "known_risks": self.known_risks,
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

class ProjectProfileService:
    """Builds a project profile from docs, git, and filesystem. Read-only. NEVER writes files. NEVER reads secrets/certs."""

    def __init__(self, workspace_path: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace_path).resolve())
        self._project_name = self._workspace.name

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

    def build(self) -> ProjectProfile:
        """Build complete project profile. Degrades gracefully on missing data."""
        source_refs: list[str] = []

        # Git info
        latest_head = self._git_head()
        source_refs.append("git:HEAD")
        origin_state = self._git_origin_state()
        source_refs.append("git:origin")

        # Docs
        project_state = self._read_doc("docs/project-state.md")
        source_refs.append("docs/project-state.md")
        current_milestone = self._extract_milestone(project_state)
        hard_rules = self._extract_hard_rules(project_state)
        known_risks = self._extract_risks(project_state)

        # Latest review gate
        latest_gate = self._find_latest_review_gate()
        if latest_gate:
            source_refs.append(latest_gate)

        # Tech stack detection
        tech_stack = self._detect_tech_stack()
        source_refs.append("filesystem:pyproject.toml|package.json")

        # Key commands
        key_commands = self._detect_key_commands()
        source_refs.append("filesystem:scripts")

        # Important docs
        important_docs = self._list_docs()
        if important_docs:
            source_refs.append("filesystem:docs/")

        return ProjectProfile(
            project_name=self._project_name,
            workspace_path=str(self._workspace),
            current_milestone=current_milestone,
            latest_head=latest_head,
            origin_state=origin_state,
            tech_stack=tech_stack,
            key_commands=key_commands,
            hard_rules=hard_rules,
            important_docs=important_docs,
            latest_review_gate=latest_gate or "未找到",
            known_risks=known_risks,
            source_refs=source_refs,
        )

    # ── Git helpers ───────────────────────────────────────────────────

    def _git_head(self) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True, cwd=str(self._workspace),
                timeout=10,
            )
            return result.stdout.strip() or "无法获取"
        except Exception:
            return "无法获取"

    def _git_origin_state(self) -> str:
        try:
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                capture_output=True, text=True, cwd=str(self._workspace),
                timeout=10,
            )
            first_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
            return first_line or "无法获取"
        except Exception:
            return "无法获取"

    # ── Doc readers ───────────────────────────────────────────────────

    def _read_doc(self, rel_path: str) -> str:
        """Read a doc file. Returns empty string if missing or unsafe."""
        path = self._workspace / rel_path
        if not path.exists() or not _is_safe_path(path):
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _extract_milestone(self, content: str) -> str:
        """Extract current milestone from project-state."""
        if not content:
            return "未知（docs/project-state.md 缺失）"
        for line in content.split("\n"):
            if "已完成到" in line or "已完成到：" in line:
                return line.strip().lstrip("- ").lstrip("已完成到：").lstrip("已完成到")
        return "无法解析（project-state.md 格式异常）"

    def _extract_hard_rules(self, content: str) -> list[str]:
        """Extract hard rules from project-state."""
        if not content:
            return ["文档缺失：无法提取硬规则"]
        rules: list[str] = []
        in_rules = False
        for line in content.split("\n"):
            if "硬规则" in line or "长期硬规则" in line:
                in_rules = True
                continue
            if in_rules:
                if line.strip().startswith("- "):
                    rules.append(line.strip().lstrip("- "))
                elif line.strip() == "":
                    continue
                elif line.strip().startswith("##") or line.strip().startswith("#"):
                    break
        return rules if rules else ["无法解析硬规则"]

    def _extract_risks(self, content: str) -> list[str]:
        """Extract known risks from project-state."""
        if not content:
            return ["文档缺失"]
        risks: list[str] = []
        in_risks = False
        for line in content.split("\n"):
            if "已知风险" in line or "当前风险" in line:
                in_risks = True
                continue
            if in_risks:
                if line.strip().startswith("- "):
                    risks.append(line.strip().lstrip("- "))
                elif line.strip().startswith("##") or line.strip().startswith("#"):
                    break
        return risks if risks else ["未发现明确风险记录"]

    def _find_latest_review_gate(self) -> str:
        """Find the latest phase review gate doc."""
        docs_dir = self._workspace / "docs"
        if not docs_dir.exists():
            return ""
        gates = sorted(
            [f.name for f in docs_dir.glob("phase-*-review-gate.md")],
            reverse=True,
        )
        return f"docs/{gates[0]}" if gates else ""

    # ── Tech detection ────────────────────────────────────────────────

    def _detect_tech_stack(self) -> dict:
        """Detect tech stack from config files."""
        stack: dict[str, str | list[str]] = {}

        # Python
        pyproject = self._workspace / "pyproject.toml"
        if pyproject.exists() and _is_safe_path(pyproject):
            stack["python"] = "detected (pyproject.toml)"
            try:
                content = pyproject.read_text(encoding="utf-8", errors="replace")
                if "fastapi" in content.lower():
                    stack["framework"] = "FastAPI"
            except Exception:
                pass

        # Node.js / pnpm
        pkg_json = self._workspace / "package.json"
        if pkg_json.exists() and _is_safe_path(pkg_json):
            stack["nodejs"] = "detected (package.json)"
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                if isinstance(data, dict):
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "electron" in deps:
                        stack["desktop"] = "Electron"
                    if "vite" in deps or "vitest" in deps:
                        stack["bundler"] = "Vite"
                    if "typescript" in deps:
                        stack["language"] = "TypeScript + Python"
            except Exception:
                pass

        if not stack:
            stack["status"] = "未检测到标准技术栈配置文件"
        return stack

    def _detect_key_commands(self) -> dict:
        """Detect key development commands."""
        commands: dict[str, str] = {}
        pkg_json = self._workspace / "package.json"
        if pkg_json.exists() and _is_safe_path(pkg_json):
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
                for key in ["test", "build", "dev", "quality", "lint"]:
                    if key in scripts:
                        commands[key] = str(scripts[key])
            except Exception:
                pass

        if not commands:
            pyproject = self._workspace / "pyproject.toml"
            if pyproject.exists() and _is_safe_path(pyproject):
                commands["test"] = "uv run pytest"
                commands["quality"] = "pnpm run quality"

        return commands

    def _list_docs(self) -> list[str]:
        """List important doc files (top-level in docs/)."""
        docs_dir = self._workspace / "docs"
        if not docs_dir.exists():
            return ["docs/ 目录不存在"]

        important: list[str] = []
        for f in sorted(docs_dir.iterdir()):
            if f.is_file() and f.suffix in (".md", ".txt") and _is_safe_path(f):
                important.append(f"docs/{f.name}")
        return important[:20]  # limit to avoid bloat
