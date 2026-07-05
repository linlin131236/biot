"""Skill system: manifest parsing, store, and selection.

Skills enhance planner context only — they cannot bypass PermissionGate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SkillManifest:
    name: str
    triggers: list[str]
    required_tools: list[str] = field(default_factory=list)
    version: str = "1.0"
    path: str = ""
    docs: str = ""

    @classmethod
    def from_skill_md(cls, text: str, path: str = "") -> "SkillManifest | None":
        """Parse SKILL.md frontmatter."""
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return None
        meta = {}
        for line in m.group(1).strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
                meta[key] = val
        name = meta.get("name")
        if not name or not isinstance(name, str):
            return None
        # Reject bypass_permission
        if meta.get("bypass_permission") in (True, "true", "True"):
            return None
        triggers = meta.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [triggers]
        required_tools = meta.get("required_tools", [])
        if isinstance(required_tools, str):
            required_tools = [required_tools]
        # Extract docs body after frontmatter
        docs = text.split("---", 2)[-1].strip() if text.count("---") >= 2 else ""
        return cls(
            name=name, triggers=triggers,
            required_tools=required_tools,
            version=str(meta.get("version", "1.0")),
            path=path, docs=docs,
        )


class SkillStore:
    """Load and query skill manifests from a directory."""

    def __init__(self, skills_dir: str) -> None:
        self._dir = Path(skills_dir)
        self._skills: list[SkillManifest] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._dir.is_dir():
            return
        for skill_path in sorted(self._dir.iterdir()):
            if not skill_path.is_dir():
                continue
            md = skill_path / "SKILL.md"
            if not md.is_file():
                continue
            try:
                text = md.read_text(encoding="utf-8")
            except OSError:
                continue
            manifest = SkillManifest.from_skill_md(text, str(skill_path))
            if manifest:
                self._skills.append(manifest)

    def list(self) -> list[SkillManifest]:
        self._ensure_loaded()
        return list(self._skills)

    def match(self, query: str) -> list[SkillManifest]:
        self._ensure_loaded()
        query_lower = query.lower()
        results = []
        for skill in self._skills:
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    results.append(skill)
                    break
        return results

    def load(self, name_or_path: str) -> SkillManifest | None:
        """Load by skill name. Rejects path traversal."""
        if "/" in name_or_path or "\\" in name_or_path or ".." in name_or_path:
            return None
        self._ensure_loaded()
        for skill in self._skills:
            if skill.name == name_or_path:
                return skill
        return None


class SkillSelector:
    """Select skills relevant to a goal/context."""

    def __init__(self, store: SkillStore) -> None:
        self._store = store

    def select(self, context: str, max_skills: int = 3) -> list[SkillManifest]:
        matches = self._store.match(context)
        return matches[:max_skills]
