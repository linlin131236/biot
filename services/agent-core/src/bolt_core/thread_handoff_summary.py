"""Thread Handoff Summary Service. Generates new-window handoff summaries.

Wraps M76 ContextCompaction to produce structured handoff documents
suitable for new AI windows to understand project state immediately.
Markdown and JSON output. No secrets. No entire history dump.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class HandoffSummary:
    """Structured handoff summary for new window context recovery."""
    workspace_dir: str
    head_state: str
    origin_state: str
    completed_milestones: list[str]
    active_prohibitions: list[str]
    required_docs: list[str]
    latest_review_gate: str
    unresolved_risks: list[str]
    next_steps: list[str]
    source_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "workspace_dir": self.workspace_dir,
            "head_state": self.head_state,
            "origin_state": self.origin_state,
            "completed_milestones": self.completed_milestones,
            "active_prohibitions": self.active_prohibitions,
            "required_docs": self.required_docs,
            "latest_review_gate": self.latest_review_gate,
            "unresolved_risks": self.unresolved_risks,
            "next_steps": self.next_steps,
            "source_refs": self.source_refs,
        }

    def to_markdown(self) -> str:
        """Render as Chinese Markdown handoff document."""
        lines: list[str] = []
        lines.append("# Bolt 项目接手摘要")
        lines.append("")
        lines.append("> 此摘要为只读上下文恢复文档。新窗口 AI 请先读取本文了解项目状态。")
        lines.append("> **不自动执行、不自动 push、不进入未授权 milestone。**")
        lines.append("")
        lines.append("## 工作目录")
        lines.append(f"`{self.workspace_dir}`")
        lines.append("")
        lines.append("## Git 状态")
        lines.append(f"- HEAD：{self.head_state}")
        lines.append(f"- Origin：{self.origin_state}")
        lines.append("")
        lines.append("## 已完成 Milestone")
        for m in self.completed_milestones:
            lines.append(f"- {m}")
        lines.append("")
        lines.append("## 当前禁止事项")
        for p in self.active_prohibitions:
            lines.append(f"- ❌ {p}")
        lines.append("")
        lines.append("## 必读文档")
        for d in self.required_docs:
            lines.append(f"- `{d}`")
        lines.append("")
        lines.append(f"## 最新 Review Gate\n`{self.latest_review_gate}`")
        lines.append("")
        if self.unresolved_risks:
            lines.append("## 未解决风险")
            for r in self.unresolved_risks:
                lines.append(f"- ⚠️ {r}")
            lines.append("")
        lines.append("## 下一步建议")
        for s in self.next_steps:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("## 参考来源")
        for r in self.source_refs:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("---")
        lines.append("*此摘要由 M77 ThreadHandoffSummary 生成。不包含 secret。不把整个历史粘贴出来。*")
        return "\n".join(lines)


class ThreadHandoffSummaryService:
    """Generates structured handoff summaries for new AI windows.

    Wraps M76 ContextCompaction for context data.
    Adds git status, prohibitions, required docs, and next steps.
    NEVER includes secrets. NEVER dumps entire history.
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

    def generate(self) -> HandoffSummary:
        """Generate a complete handoff summary."""
        source_refs: list[str] = []

        # ── Project Profile ─────────────────────────────────────────
        from bolt_core.project_profile import ProjectProfileService
        profile_svc = ProjectProfileService(self._workspace)
        profile = profile_svc.build()
        source_refs.extend(profile.source_refs)

        # ── Context Compaction ──────────────────────────────────────
        from bolt_core.context_compaction import ContextCompactionService
        compaction_svc = ContextCompactionService(self._workspace)
        compact = compaction_svc.compact(max_items=30)
        source_refs.extend(compact.source_refs)

        # ── Git state ──────────────────────────────────────────────
        head_state = profile.latest_head
        origin_state = profile.origin_state

        # ── Required docs ───────────────────────────────────────────
        required_docs = [
            "docs/project-state.md",
            "docs/桌面AI编程Agent全流程架构对比.md",
            profile.latest_review_gate if profile.latest_review_gate != "未找到" else "",
        ]
        required_docs = [d for d in required_docs if d]

        # ── Active prohibitions (from hard rules) ────────────────────
        prohibitions = [
            "不自动 push、release、tag、delete。",
            "不自动批准权限。不绕过 PermissionGate。",
            "不进入未授权 milestone。",
            "不使用 as any / unknown as。",
            "renderer 不暴露 ipcRenderer / fs / shell / process。",
            "不提交生成物、缓存、虚拟环境、证书材料、.bolt、uv.lock。",
            "不提交 .claude/，除非用户明确授权。",
            "记忆系统不得保存 secret/token/cert/private key。",
            "不自动执行危险命令。",
        ]

        # ── Unresolved risks ─────────────────────────────────────────
        unresolved = profile.known_risks if profile.known_risks else ["无记录"]

        # ── Next steps ───────────────────────────────────────────────
        next_steps = [
            "1. 读取 docs/project-state.md 了解当前状态。",
            "2. 读取最新 review gate 了解验收状态。",
            "3. 运行 git status --short --branch 确认工作区状态。",
            "4. 运行 git log --oneline -10 --decorate 了解提交历史。",
            "5. 等待用户确认后再开始实现或审查。",
        ]

        return HandoffSummary(
            workspace_dir=str(self._workspace),
            head_state=head_state,
            origin_state=origin_state,
            completed_milestones=compact.completed_milestones[:20],
            active_prohibitions=prohibitions,
            required_docs=required_docs,
            latest_review_gate=profile.latest_review_gate,
            unresolved_risks=unresolved,
            next_steps=next_steps,
            source_refs=source_refs,
        )
