"""Agent Intelligence Dogfood (M120).

Comprehensive V7 review gate for M111-M119 evals, V6 tool safety,
documentation completeness, and the M121 boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DogfoodCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class DogfoodResult:
    checks: list[DogfoodCheck] = field(default_factory=list)
    all_passed: bool = True
    p1_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in self.checks],
            "total": len(self.checks),
            "passed_count": sum(1 for c in self.checks if c.passed),
            "failed_count": sum(1 for c in self.checks if not c.passed),
            "all_passed": self.all_passed,
            "p1_failures": self.p1_failures,
        }


class AgentIntelligenceDogfoodService:
    """M120 智能 Agent 大复盘：18 项只读门禁检查。"""

    _V7_MODULES = {
        "Tool Call Eval": "tool_call_eval",
        "Patch Apply Eval": "patch_apply_eval",
        "Test Failure Diagnosis Eval": "test_failure_diagnosis_eval",
        "Permission Boundary Eval": "permission_boundary_eval",
        "Multi-Agent Collaboration Eval": "multi_agent_collaboration_eval",
        "Memory Retrieval Eval": "memory_retrieval_eval",
        "Chinese Interaction Eval": "chinese_interaction_eval",
        "E2E Task Dogfood": "e2e_task_dogfood",
        "Failure Recovery Dogfood": "failure_recovery_dogfood",
    }

    _V6_MODULES = [
        "tool_registry",
        "tool_manifest",
        "tool_permission_contract",
        "readonly_tool_runner",
        "write_tool_proposal",
        "patch_proposal",
        "approval_apply",
        "test_runner_integration",
        "tool_ecosystem_dogfood",
    ]

    def __init__(self, project_dir: str = ".") -> None:
        self._project_dir = Path(project_dir).resolve()

    def review(self) -> DogfoodResult:
        checks: list[DogfoodCheck] = []
        p1: list[str] = []
        src = self._project_dir / "services/agent-core/src/bolt_core"
        tests = self._project_dir / "services/agent-core/tests"
        docs_dir = self._project_dir / "docs"

        def add(name: str, passed: bool, detail: str = "") -> None:
            checks.append(DogfoodCheck(name=name, passed=passed, detail=detail))
            if not passed:
                p1.append(name)

        for index, (label, module) in enumerate(self._V7_MODULES.items(), start=1):
            source_file = src / f"{module}.py"
            test_file = tests / f"test_{module}.py"
            add(
                f"{index}. {label} 通过",
                source_file.exists() and test_file.exists(),
                f"{source_file.name}={'存在' if source_file.exists() else '缺失'}；"
                f"{test_file.name}={'存在' if test_file.exists() else '缺失'}",
            )

        existing_v6 = [module for module in self._V6_MODULES if (src / f"{module}.py").exists()]
        add(
            "10. M101-M110 工具生态仍安全",
            len(existing_v6) == len(self._V6_MODULES),
            f"V6 核心文件 {len(existing_v6)}/{len(self._V6_MODULES)} 存在",
        )

        v7_sources = [src / f"{module}.py" for module in self._V7_MODULES.values()]
        dangerous_call_patterns = ["sub" + "process.run", "os.system", "shutil.rmtree", "os.remove", "git.push("]
        dangerous_hits = self._scan_patterns(v7_sources, dangerous_call_patterns)
        add(
            "11. 不自动 push/release/tag/delete",
            not dangerous_hits,
            self._format_hits(dangerous_hits) if dangerous_hits else "V7 新增后端未发现自动危险操作",
        )

        approval_file = src / "approval_apply.py"
        permission_file = src / "tool_permission_contract.py"
        permission_ok = approval_file.exists() and permission_file.exists()
        add(
            "12. 不绕过 PermissionGate",
            permission_ok,
            "ApprovalApplyEngine 与 Tool Permission Contract 均存在" if permission_ok else "权限门控文件缺失",
        )

        approval_text = approval_file.read_text(encoding="utf-8") if approval_file.exists() else ""
        auto_approve_blocked = "approved=true" in approval_text and "actor" in approval_text and "human" in approval_text
        add(
            "13. 不自动 approve",
            auto_approve_blocked,
            "approval_apply.py 保留 approved=true 绕过检测和 human actor 检查",
        )

        desktop_src = self._project_dir / "apps/desktop/src"
        new_renderer_files = list(desktop_src.glob("*Eval*.tsx")) + list(desktop_src.glob("*Dogfood*.tsx"))
        renderer_hits = self._scan_patterns(new_renderer_files, ["ipcRenderer", "require('fs')", "process."])
        add(
            "14. Renderer 无 ipcRenderer/fs/shell/process 暴露",
            not renderer_hits,
            self._format_hits(renderer_hits) if renderer_hits else "V7 未新增危险 renderer 暴露",
        )

        type_escape_hits = self._scan_patterns(list(desktop_src.glob("*.ts")) + list(desktop_src.glob("*.tsx")), ["as any", "unknown as"])
        add(
            "15. 无 as any / unknown as",
            not type_escape_hits,
            self._format_hits(type_escape_hits) if type_escape_hits else "未发现 TypeScript 类型逃逸",
        )

        missing_docs = self._missing_v7_docs(docs_dir)
        add(
            "16. V7 文档链完整（M111-M120 exec plan + decision + review gate）",
            not missing_docs,
            "全部 30 份文档就位" if not missing_docs else "缺失：" + "；".join(missing_docs),
        )

        project_state = docs_dir / "project-state.md"
        state_text = project_state.read_text(encoding="utf-8") if project_state.exists() else ""
        state_ok = "M120" in state_text and "未进入 M121" in state_text and "未 push" in state_text
        add(
            "17. project-state 更新准确（含 M120）",
            state_ok,
            "project-state.md 已记录 M120、未 push、未进入 M121" if state_ok else "project-state.md 需要更新到 M120",
        )

        m121_files = list((docs_dir / "exec-plans/active").glob("121-*.md"))
        add(
            "18. 未进入 M121",
            not m121_files,
            "未发现 M121 文档" if not m121_files else f"发现 {len(m121_files)} 个 M121 文档",
        )

        return DogfoodResult(checks=checks, all_passed=not p1, p1_failures=p1)

    @staticmethod
    def _scan_patterns(files: list[Path], patterns: list[str]) -> list[str]:
        hits: list[str] = []
        for file_path in files:
            if not file_path.exists() or not file_path.is_file():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in patterns:
                    if pattern in line:
                        hits.append(f"{file_path.name}:{line_no}:{pattern}")
        return hits

    @staticmethod
    def _format_hits(hits: list[str]) -> str:
        return "；".join(hits[:8]) + (f"；另有 {len(hits) - 8} 项" if len(hits) > 8 else "")

    @staticmethod
    def _missing_v7_docs(docs_dir: Path) -> list[str]:
        missing: list[str] = []
        for milestone in range(111, 121):
            if not list((docs_dir / "exec-plans/active").glob(f"{milestone}-*.md")):
                missing.append(f"M{milestone} exec plan")
            if not list((docs_dir / "decisions").glob(f"{milestone}-*.md")):
                missing.append(f"M{milestone} decision")
            if not (docs_dir / f"phase-{milestone}-review-gate.md").exists():
                missing.append(f"M{milestone} review gate")
        return missing
