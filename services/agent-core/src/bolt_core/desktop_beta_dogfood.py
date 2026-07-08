"""Desktop Beta Dogfood (M100). Grand review gate for M91-M99 desktop panels.

Validates all V5 components before allowing entry to M101.
13 readiness checks covering all M91-M99 panels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re


@dataclass
class DogfoodCheck:
    check_id: str
    label_cn: str
    passed: bool
    details_cn: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class DogfoodResult:
    checks: list[DogfoodCheck]
    total: int
    passed: int
    failed: int
    ready_for_next: bool
    summary_cn: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "checks": [{"check_id": c.check_id, "label_cn": c.label_cn,
                         "passed": c.passed, "details_cn": c.details_cn,
                         "evidence": c.evidence} for c in self.checks],
            "total": self.total, "passed": self.passed, "failed": self.failed,
            "ready_for_next": self.ready_for_next, "summary_cn": self.summary_cn,
            "created_at": self.created_at,
        }


class DesktopBetaDogfoodService:
    """Validates M91-M99 desktop panel readiness."""

    def __init__(self, project_dir: str | Path | None = None) -> None:
        self._project_dir = Path(project_dir) if project_dir is not None else Path(__file__).resolve().parents[4]

    def run(self) -> DogfoodResult:
        checks: list[DogfoodCheck] = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # M91: Task Home
        checks.append(self._panel_check("m91_task_home", "中文任务首页", 91, [
            "apps/desktop/src/TaskHomePanel.tsx",
            "apps/desktop/src/TaskHomePanel.test.tsx",
            "services/agent-core/src/bolt_core/task_home.py",
            "services/agent-core/src/bolt_core/task_home_api.py",
        ], "create_task_home_router"))

        # M92: Permission Center
        checks.append(self._panel_check("m92_permission_center", "权限中心", 92, [
            "apps/desktop/src/PermissionCenterPanel.tsx",
            "apps/desktop/src/PermissionCenterPanel.test.tsx",
            "services/agent-core/src/bolt_core/permission_center.py",
            "services/agent-core/src/bolt_core/permission_center_api.py",
        ], "create_permission_center_router"))

        # M93: Audit Timeline
        checks.append(self._panel_check("m93_audit_timeline", "审计时间线视图", 93, [
            "apps/desktop/src/AuditTimelinePanel.tsx",
            "apps/desktop/src/AuditTimelinePanel.test.tsx",
            "services/agent-core/src/bolt_core/audit_timeline_api.py",
        ], "create_audit_timeline_router"))

        # M94: Diagnostics Center
        checks.append(self._panel_check("m94_diagnostics", "诊断中心", 94, [
            "apps/desktop/src/DiagnosticsCenterPanel.tsx",
            "apps/desktop/src/DiagnosticsCenterPanel.test.tsx",
            "services/agent-core/src/bolt_core/diagnostics_center_api.py",
        ], "create_diagnostics_center_router"))

        # M95: Release Readiness
        checks.append(self._panel_check("m95_release_readiness", "发布准备页", 95, [
            "apps/desktop/src/ReleaseReadinessPanel.tsx",
            "apps/desktop/src/ReleaseReadinessPanel.test.tsx",
            "services/agent-core/src/bolt_core/release_readiness_api.py",
        ], "create_release_readiness_router"))

        # M96: Multi Task Queue
        checks.append(self._panel_check("m96_multi_task_queue", "多任务队列", 96, [
            "apps/desktop/src/MultiTaskQueuePanel.tsx",
            "apps/desktop/src/MultiTaskQueuePanel.test.tsx",
            "services/agent-core/src/bolt_core/multi_task_queue_api.py",
        ], "create_multi_task_queue_router"))

        # M97: Failure Explanation
        checks.append(self._panel_check("m97_failure_explanation", "失败解释体验", 97, [
            "apps/desktop/src/FailureExplanationPanel.tsx",
            "apps/desktop/src/FailureExplanationPanel.test.tsx",
            "services/agent-core/src/bolt_core/failure_explanation_api.py",
        ], "create_failure_explanation_router"))

        # M98: Session Recovery
        checks.append(self._panel_check("m98_session_recovery", "会话恢复体验", 98, [
            "apps/desktop/src/SessionRecoveryPanel.tsx",
            "apps/desktop/src/SessionRecoveryPanel.test.tsx",
            "services/agent-core/src/bolt_core/session_recovery_api.py",
        ], "create_session_recovery_router"))

        # M99: Settings Tools
        checks.append(self._panel_check("m99_settings_tools", "设置/模型/工具面板", 99, [
            "apps/desktop/src/SettingsToolsPanel.tsx",
            "apps/desktop/src/SettingsToolsPanel.test.tsx",
            "services/agent-core/src/bolt_core/settings_tools_api.py",
        ], "create_settings_tools_router"))

        # Cross-cutting checks
        checks.append(self._chinese_ui_check())

        checks.append(self._renderer_safety_check())

        checks.append(self._no_auto_execution_check())

        checks.append(self._not_entered_m101_check())

        passed = sum(1 for c in checks if c.passed)
        failed = len(checks) - passed

        return DogfoodResult(
            checks=checks,
            total=len(checks),
            passed=passed,
            failed=failed,
            ready_for_next=failed == 0,
            summary_cn=f"V5 桌面 Beta Dogfood：{passed}/{len(checks)} 项通过。{'✅ 准备就绪，等待用户复审。' if failed == 0 else f'❌ {failed} 项未通过。'}",
            created_at=now,
        )

    def _check(self, check_id: str, label_cn: str, details_cn: str, passed: bool, evidence: list[str]) -> DogfoodCheck:
        return DogfoodCheck(check_id=check_id, label_cn=label_cn, passed=passed, details_cn=details_cn, evidence=evidence)

    def _panel_check(self, check_id: str, label_cn: str, milestone: int, paths: list[str], router_name: str) -> DogfoodCheck:
        missing = [p for p in paths if not self._exists(p)]
        docs_missing = self._missing_docs(milestone)
        route_registered = self._app_contains(router_name)
        passed = not missing and not docs_missing and route_registered
        problems: list[str] = []
        if missing:
            problems.append(f"缺少文件：{', '.join(missing)}")
        if docs_missing:
            problems.append(f"缺少文档：{', '.join(docs_missing)}")
        if not route_registered:
            problems.append(f"app.py 未注册 {router_name}")
        detail = f"M{milestone} {label_cn} 文件、路由和文档链完整。" if passed else "；".join(problems)
        return self._check(check_id, label_cn, detail, passed, paths)

    def _missing_docs(self, milestone: int) -> list[str]:
        prefix = f"{milestone:03d}-*.md"
        missing: list[str] = []
        if not list((self._project_dir / "docs" / "exec-plans" / "active").glob(prefix)):
            missing.append(f"docs/exec-plans/active/{prefix}")
        if not list((self._project_dir / "docs" / "decisions").glob(prefix)):
            missing.append(f"docs/decisions/{prefix}")
        if not self._exists(f"docs/phase-{milestone}-review-gate.md"):
            missing.append(f"docs/phase-{milestone}-review-gate.md")
        return missing

    def _chinese_ui_check(self) -> DogfoodCheck:
        panels = self._panel_paths()
        missing_chinese = [p for p in panels if not self._has_chinese(p)]
        passed = not missing_chinese
        detail = "所有 M91-M99 面板包含中文文案。" if passed else f"缺少中文文案：{', '.join(missing_chinese)}"
        return self._check("cross_chinese_ui", "全中文 UI", detail, passed, panels)

    def _renderer_safety_check(self) -> DogfoodCheck:
        patterns = [
            re.compile(r"\bipcRenderer\b"),
            re.compile(r"require\(['\"]fs['\"]\)"),
            re.compile(r"require\(['\"]child_process['\"]\)"),
            re.compile(r"\bprocess\."),
            re.compile(r"\bas\s+any\b"),
            re.compile(r"\bunknown\s+as\b"),
        ]
        hits = self._scan_panel_code(patterns)
        passed = not hits
        detail = "所有面板无 renderer 危险 API 和类型逃逸。" if passed else f"发现风险命中：{', '.join(hits)}"
        return self._check("cross_no_danger_api", "Renderer 无危险 API", detail, passed, self._panel_paths())

    def _no_auto_execution_check(self) -> DogfoodCheck:
        patterns = [
            re.compile(r"\brunAgentLoop\b"),
            re.compile(r"\bapprovePermission\b"),
            re.compile(r"\bapprove_permission\b"),
            re.compile(r"\bgit\s+push\b"),
            re.compile(r"\bgh\s+release\b"),
            re.compile(r"\bgit\s+tag\b"),
            re.compile(r"\bRemove-Item\b"),
            re.compile(r"\brm\s+-rf\b"),
        ]
        hits = self._scan_panel_code(patterns)
        passed = not hits
        detail = "所有面板无自动执行、自动批准、push/release/tag/delete 入口。" if passed else f"发现风险命中：{', '.join(hits)}"
        return self._check("cross_no_auto_approve", "无自动批准/执行", detail, passed, self._panel_paths())

    def _not_entered_m101_check(self) -> DogfoodCheck:
        state = self._read("docs/project-state.md")
        has_m101_commit = self._app_contains("M101")
        passed = "未进入 M101" in state and not has_m101_commit
        detail = "project-state 明确 M100 后停止，未进入 M101。" if passed else "project-state 或代码中出现 M101 进行中迹象。"
        return self._check("cross_not_entered_m101", "未进入 M101", detail, passed, ["docs/project-state.md"])

    def _panel_paths(self) -> list[str]:
        return [
            "apps/desktop/src/TaskHomePanel.tsx",
            "apps/desktop/src/PermissionCenterPanel.tsx",
            "apps/desktop/src/AuditTimelinePanel.tsx",
            "apps/desktop/src/DiagnosticsCenterPanel.tsx",
            "apps/desktop/src/ReleaseReadinessPanel.tsx",
            "apps/desktop/src/MultiTaskQueuePanel.tsx",
            "apps/desktop/src/FailureExplanationPanel.tsx",
            "apps/desktop/src/SessionRecoveryPanel.tsx",
            "apps/desktop/src/SettingsToolsPanel.tsx",
        ]

    def _scan_panel_code(self, patterns: list[re.Pattern[str]]) -> list[str]:
        hits: list[str] = []
        for rel in self._panel_paths():
            text = self._strip_comments(self._read(rel))
            for pattern in patterns:
                if pattern.search(text):
                    hits.append(f"{rel}:{pattern.pattern}")
        return hits

    def _strip_comments(self, text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return re.sub(r"//.*", "", text)

    def _has_chinese(self, rel: str) -> bool:
        return any("\u4e00" <= c <= "\u9fff" for c in self._read(rel))

    def _app_contains(self, needle: str) -> bool:
        return needle in self._read("services/agent-core/src/bolt_core/app.py")

    def _exists(self, rel: str) -> bool:
        return (self._project_dir / rel).exists()

    def _read(self, rel: str) -> str:
        path = self._project_dir / rel
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
