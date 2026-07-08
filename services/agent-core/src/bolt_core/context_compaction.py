"""Context Compaction Service. Produces structured compact summaries.

Composes data from all memory layers:
- Project Profile (M71)
- Code Map Index (M72)
- Decision Memory (M73)
- Failure Memory Index (M74)
- User Preference Memory (M75)

Output: structured compact summary with token budget support.
Chinese output. Safety hard rules preserved. No LLM required by default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CompactSummary:
    """Structured compact summary of project context."""
    objective: str
    current_state: str
    completed_milestones: list[str]
    active_constraints: list[str]
    relevant_decisions: list[dict]
    known_failures: list[dict]
    user_preferences: list[dict]
    next_actions: list[str]
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "current_state": self.current_state,
            "completed_milestones": self.completed_milestones,
            "active_constraints": self.active_constraints,
            "relevant_decisions": self.relevant_decisions,
            "known_failures": self.known_failures,
            "user_preferences": self.user_preferences,
            "next_actions": self.next_actions,
            "source_refs": self.source_refs,
        }

    def to_markdown(self) -> str:
        """Render as Chinese Markdown summary."""
        lines: list[str] = []
        lines.append("# 项目上下文压缩摘要")
        lines.append("")
        lines.append(f"## 目标\n{self.objective}")
        lines.append("")
        lines.append(f"## 当前状态\n{self.current_state}")
        lines.append("")
        lines.append("## 已完成 Milestone")
        for m in self.completed_milestones:
            lines.append(f"- {m}")
        lines.append("")
        lines.append("## 活跃约束（安全硬规则）")
        for c in self.active_constraints:
            lines.append(f"- {c}")
        lines.append("")
        if self.relevant_decisions:
            lines.append("## 相关决策")
            for d in self.relevant_decisions[:5]:
                lines.append(f"- **{d.get('milestone', '?')}** {d.get('title', '?')}: {d.get('summary_cn', '?')[:120]}")
            lines.append("")
        if self.known_failures:
            lines.append("## 已知失败模式")
            for f in self.known_failures[:5]:
                lines.append(f"- [{f.get('severity', '?')}] {f.get('symptom_cn', '?')[:150]}")
            lines.append("")
        if self.user_preferences:
            lines.append("## 用户偏好")
            for p in self.user_preferences:
                lines.append(f"- [{p.get('category', '?')}] {p.get('statement_cn', '?')[:120]}")
            lines.append("")
        lines.append("## 下一步建议")
        for a in self.next_actions:
            lines.append(f"- {a}")
        lines.append("")
        lines.append("## 参考来源")
        for r in self.source_refs:
            lines.append(f"- {r}")
        return "\n".join(lines)


class ContextCompactionService:
    """Produces compact structured summaries from all memory layers.

    Composition over generation: reads from existing services, assembles.
    No LLM calls. Token budget via max_items truncation.
    Safety hard rules always preserved (never truncated).
    """

    def __init__(self, workspace_path: str | Path) -> None:
        self._workspace = self._find_project_root(Path(workspace_path).resolve())

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

    def compact(
        self,
        max_items: int = 50,
        focus_milestones: Optional[list[str]] = None,
    ) -> CompactSummary:
        """Produce a compact summary from all memory layers.

        Args:
            max_items: Max items per section (safety rules excluded from limit)
            focus_milestones: Optional list of milestones to focus on
        """
        source_refs: list[str] = []

        # ── Project Profile (M71) ──────────────────────────────────
        from bolt_core.project_profile import ProjectProfileService
        profile_svc = ProjectProfileService(self._workspace)
        profile = profile_svc.build()
        source_refs.extend(profile.source_refs)

        # ── Decision Memory (M73) ──────────────────────────────────
        from bolt_core.decision_memory import DecisionMemoryService
        decision_svc = DecisionMemoryService(self._workspace)
        all_decisions = decision_svc.list_all()
        source_refs.append("docs/decisions/*.md")

        # ── Failure Memory (M74) ───────────────────────────────────
        from bolt_core.failure_memory_index import FailureMemoryIndexService
        failure_svc = FailureMemoryIndexService(self._workspace)
        all_failures = failure_svc.list_all()
        source_refs.append("docs/phase-*-review-gate.md")

        # ── User Preferences (M75) ─────────────────────────────────
        from bolt_core.user_preference_memory import UserPreferenceMemoryService
        pref_svc = UserPreferenceMemoryService(self._workspace)
        all_prefs = pref_svc.list_all()
        source_refs.append("docs/project-state.md")

        # ── Build sections ─────────────────────────────────────────

        # Objective: from product direction preference
        objective = "Biot 桌面 AI 编程 Agent：Claude 的安全粒度 + Codex 的流畅执行。信任但验证。"
        for p in all_prefs:
            if p.category == "product_direction":
                objective = p.statement_cn
                break

        # Current state: from project profile
        current_state = (
            f"项目：{profile.project_name}，工作区：{profile.workspace_path}。"
            f"当前 milestone：{profile.current_milestone}。"
            f"最新 HEAD：{profile.latest_head}。"
            f"Origin 状态：{profile.origin_state}。"
        )

        # Completed milestones: from profile + decision records
        completed = [profile.current_milestone]
        seen = {profile.current_milestone}
        for d in all_decisions:
            m = d.milestone
            if m not in seen and m != "未知":
                completed.append(m)
                seen.add(m)
        completed = completed[:max(max_items, 20)]

        # Active constraints: safety hard rules ALWAYS preserved
        constraints = list(profile.hard_rules) if profile.hard_rules else []
        # Ensure key safety rules are present
        key_rules = [
            "所有用户可见 UI 必须中文。",
            "不自动 push、release、tag、delete。",
            "不自动批准权限。不绕过 PermissionGate。",
            "不进入未授权 milestone。",
            "不使用 as any / unknown as。",
            "renderer 不暴露 ipcRenderer / fs / shell / process。",
            "记忆系统不得保存 secret/token/cert/private key。",
        ]
        for rule in key_rules:
            if not any(rule[:15] in c for c in constraints):
                constraints.append(rule)

        # Relevant decisions: focus on recent or specified milestones
        if focus_milestones:
            relevant = [d for d in all_decisions if d.milestone in focus_milestones]
        else:
            # Last 10 milestone decisions
            relevant = sorted(all_decisions, key=lambda d: d.decision_id, reverse=True)[:max_items]
        decision_dicts = [
            {"milestone": d.milestone, "title": d.title,
             "summary_cn": d.summary_cn, "source_refs": d.source_refs}
            for d in relevant[:max_items]
        ]

        # Known failures: P1/P2 first, then P3
        p1p2 = [f for f in all_failures if f.severity in ("P1", "P2")]
        p3 = [f for f in all_failures if f.severity == "P3"]
        failures = p1p2 + p3
        failure_dicts = [
            {"failure_id": f.failure_id, "severity": f.severity,
             "category": f.category, "symptom_cn": f.symptom_cn,
             "fix_summary_cn": f.fix_summary_cn, "source_refs": f.source_refs}
            for f in failures[:max_items]
        ]

        # User preferences
        pref_dicts = [
            {"category": p.category, "statement_cn": p.statement_cn,
             "source_refs": p.source_refs}
            for p in all_prefs
        ]

        # Next actions
        next_actions = [
            "按 milestone 顺序继续执行。",
            "每个 milestone 后执行 targeted tests + review gate。",
            "不自动 push，等待用户明确授权。",
            "M80 Memory Dogfood 是大复盘门，M80 不通过不准进入 M81。",
        ]

        return CompactSummary(
            objective=objective,
            current_state=current_state,
            completed_milestones=completed,
            active_constraints=constraints,
            relevant_decisions=decision_dicts,
            known_failures=failure_dicts,
            user_preferences=pref_dicts,
            next_actions=next_actions,
            source_refs=source_refs,
        )

    def estimate_tokens(self, summary: CompactSummary) -> int:
        """Estimate token count (rough: ~1.3 chars per token for Chinese)."""
        text = summary.to_markdown()
        # Chinese text: ~1.3 characters per token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text)
        # Rough estimate
        return int(chinese_chars * 0.7 + (total_chars - chinese_chars) * 0.25)
