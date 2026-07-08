"""Product Workbench Dogfood (M130)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from bolt_core.product_workbench import ProductWorkbenchService


@dataclass(frozen=True)
class DogfoodCheck:
    check_id: str
    label_cn: str
    passed: bool
    detail_cn: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "label_cn": self.label_cn,
            "passed": self.passed,
            "detail_cn": self.detail_cn,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class ProductWorkbenchDogfoodResult:
    total: int
    passed: int
    failed: int
    ready_for_review: bool
    summary_cn: str
    checks: list[DogfoodCheck]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "ready_for_review": self.ready_for_review,
            "summary_cn": self.summary_cn,
            "checks": [check.to_dict() for check in self.checks],
        }


class ProductWorkbenchDogfoodService:
    """Checks M126-M129 product workbench readiness."""

    def __init__(self, project_dir: str | Path | None = None) -> None:
        candidate = Path(project_dir).resolve() if project_dir is not None else Path(__file__).resolve().parents[4]
        self._project_dir = self._resolve_project_dir(candidate)

    def run(self) -> ProductWorkbenchDogfoodResult:
        snapshot = ProductWorkbenchService(self._project_dir).snapshot().to_dict()
        checks = [
            self._exists_check("workbench_api_files", "工作台后端文件存在", [
                "services/agent-core/src/bolt_core/product_workbench.py",
                "services/agent-core/src/bolt_core/product_workbench_api.py",
            ]),
            self._contains_check("workbench_api_registered", "工作台 API 已注册",
                                 "services/agent-core/src/bolt_core/app.py", "create_product_workbench_router"),
            self._exists_check("desktop_panel_registered", "桌面工作台面板存在", [
                "apps/desktop/src/ProductWorkbenchPanel.tsx",
                "apps/desktop/src/ProductWorkbenchPanel.test.tsx",
            ]),
            self._contains_check("desktop_panel_mounted", "桌面第一屏已挂载",
                                 "apps/desktop/src/PanelsSection.tsx", "ProductWorkbenchPanel"),
            self._snapshot_check("full_stage_flow", "8 阶段流程完整", len(snapshot.get("stages", [])) == 8,
                                 "工作台必须展示从用户意图到审计恢复的完整流程。"),
            self._snapshot_check("patch_approval_visible", "补丁批准检查可见",
                                 bool(snapshot.get("patch_approval")), "patch_approval 字段必须存在。"),
            self._snapshot_check("test_feedback_visible", "白名单测试回填可见",
                                 bool(snapshot.get("test_feedback")), "test_feedback 字段必须存在。"),
            self._snapshot_check("failure_recovery_visible", "失败与恢复检查可见",
                                 bool(snapshot.get("failure_recovery")), "failure_recovery 字段必须存在。"),
            self._snapshot_check("read_only_boundary", "工作台保持只读",
                                 snapshot.get("read_only") is True, "read_only 必须为 true。"),
            self._safety_check(),
            self._docs_check(),
            self._chinese_ui_check(),
            self._no_auto_actions_check(),
        ]
        passed = sum(1 for check in checks if check.passed)
        failed = len(checks) - passed
        return ProductWorkbenchDogfoodResult(
            total=len(checks),
            passed=passed,
            failed=failed,
            ready_for_review=failed == 0,
            summary_cn=f"M126-M129 Agent 工作台 Dogfood：{passed}/{len(checks)} 项通过。",
            checks=checks,
        )

    def _exists_check(self, check_id: str, label_cn: str, rel_paths: list[str]) -> DogfoodCheck:
        missing = [rel for rel in rel_paths if not (self._project_dir / rel).exists()]
        return DogfoodCheck(check_id, label_cn, not missing,
                            "文件齐全。" if not missing else f"缺少文件：{', '.join(missing)}", rel_paths)

    def _contains_check(self, check_id: str, label_cn: str, rel_path: str, needle: str) -> DogfoodCheck:
        text = self._read(rel_path)
        passed = needle in text
        return DogfoodCheck(check_id, label_cn, passed,
                            f"{needle} 已找到。" if passed else f"{needle} 未找到。", [rel_path])

    def _snapshot_check(self, check_id: str, label_cn: str, passed: bool, detail: str) -> DogfoodCheck:
        return DogfoodCheck(check_id, label_cn, passed, detail, ["GET /product-workbench"])

    def _safety_check(self) -> DogfoodCheck:
        safety = ProductWorkbenchService(self._project_dir).snapshot().to_dict().get("safety", {})
        passed = (
            safety.get("auto_apply_allowed") is False
            and safety.get("auto_approve_allowed") is False
            and safety.get("human_approval_required") is True
            and safety.get("dangerous_operations_blocked") is True
        )
        return DogfoodCheck("safety_boundary", "安全边界完整", passed,
                            "不自动 apply、不自动 approve、写入需用户批准。" if passed else "安全字段不完整。",
                            ["product_workbench.py"])

    def _docs_check(self) -> DogfoodCheck:
        missing: list[str] = []
        for milestone in range(126, 131):
            if not list((self._project_dir / "docs/exec-plans/active").glob(f"{milestone:03d}-*.md")):
                missing.append(f"exec plan M{milestone}")
            if not list((self._project_dir / "docs/decisions").glob(f"{milestone:03d}-*.md")):
                missing.append(f"decision M{milestone}")
            if not (self._project_dir / f"docs/phase-{milestone}-review-gate.md").exists():
                missing.append(f"review gate M{milestone}")
        return DogfoodCheck("docs_complete", "M126-M130 文档链完整", not missing,
                            "文档链完整。" if not missing else f"缺少：{', '.join(missing)}", ["docs"])

    def _chinese_ui_check(self) -> DogfoodCheck:
        text = self._read("apps/desktop/src/ProductWorkbenchPanel.tsx")
        passed = any("\u4e00" <= char <= "\u9fff" for char in text)
        return DogfoodCheck("chinese_ui", "工作台 UI 为中文", passed,
                            "面板包含中文文案。" if passed else "未发现中文文案。", ["ProductWorkbenchPanel.tsx"])

    def _no_auto_actions_check(self) -> DogfoodCheck:
        text = self._strip_comments(self._read("apps/desktop/src/ProductWorkbenchPanel.tsx"))
        patterns = [
            "approve" + "Permission",
            "run" + "AgentLoop",
            r"git\s+" + "push",
            r"gh\s+" + "release",
            r"git\s+" + "tag",
            r"rm\s+" + "-rf",
        ]
        hits = [pattern for pattern in patterns if re.search(pattern, text)]
        return DogfoodCheck("no_auto_actions", "无自动执行/批准入口", not hits,
                            "未发现自动执行、自动批准、push/release/tag/delete 入口。" if not hits else f"命中：{', '.join(hits)}",
                            ["ProductWorkbenchPanel.tsx"])

    def _read(self, rel_path: str) -> str:
        try:
            return (self._project_dir / rel_path).read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _strip_comments(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return re.sub(r"//.*", "", text)

    @staticmethod
    def _resolve_project_dir(candidate: Path) -> Path:
        current = candidate.resolve()
        for path in [current, *current.parents]:
            if (path / "docs").is_dir() and (path / "apps").is_dir() and (path / "services").is_dir():
                return path
        return current
