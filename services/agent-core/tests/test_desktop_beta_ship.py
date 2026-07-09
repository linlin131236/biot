from pathlib import Path

from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.desktop_beta_ship import DesktopBetaShipService


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_project(tmp_path: Path) -> Path:
    _write(
        tmp_path / "apps/desktop/package.json",
        '{"scripts":{"build":"vite build","package:win":"electron-builder --publish never","package:win:dir":"electron-builder --dir --publish never","package:win:nsis":"electron-builder --win nsis --publish never"}}',
    )
    _write(tmp_path / "package.json", '{"scripts":{"quality":"pnpm test"}}')
    _write(tmp_path / "scripts/check-desktop-package-runtime.mjs", "console.log('ok')")
    _write(tmp_path / "scripts/release-preflight.mjs", "console.log('ok')")
    _write(tmp_path / "apps/desktop/src/LiquidGlassWorkbench.tsx", "首次启动 工作区")
    _write(tmp_path / "apps/desktop/src/LiquidGlassSettings.tsx", "模型设置 API Key 代理")
    _write(tmp_path / "apps/desktop/src/PermissionCenterPanel.tsx", "人工批准 权限")
    _write(tmp_path / "apps/desktop/src/PatchPreviewPanel.tsx", "补丁预览")
    _write(tmp_path / "apps/desktop/src/TestRunnerPanel.tsx", "安全测试")
    _write(tmp_path / "apps/desktop/src/DiagnosticsCenterPanel.tsx", "连接失败 模型失败")
    _write(tmp_path / "apps/desktop/src/SessionRecoveryPanel.tsx", "会话恢复")
    _write(tmp_path / "apps/desktop/src/AuditTimelinePanel.tsx", "审计时间线")
    _write(tmp_path / "apps/desktop/src/TaskResultSummaryPanel.tsx", "任务结果")
    _write(tmp_path / "apps/desktop/src/ProductWorkbenchPanel.tsx", "产品工作台")
    _write(tmp_path / "apps/desktop/src/App.test.tsx", "render")
    _write(tmp_path / "apps/desktop/src/dogfoodSmoke.test.ts", "dogfood")
    _write(tmp_path / "apps/desktop/src/uiWorkflowDogfood.test.tsx", "workflow")
    _write(tmp_path / "apps/desktop/src/LiquidGlassWorkbench.test.tsx", "workbench")
    for index in range(7):
        _write(tmp_path / f"apps/desktop/src/ShipFixture{index}.test.tsx", "fixture")
    _write(tmp_path / "services/agent-core/src/bolt_core/desktop_settings.py", "settings")
    _write(tmp_path / "services/agent-core/src/bolt_core/desktop_settings_api.py", "settings")
    _write(tmp_path / "services/agent-core/src/bolt_core/release_readiness.py", "readiness")
    _write(tmp_path / "services/agent-core/src/bolt_core/public_beta_readiness.py", "beta")
    _write(tmp_path / "docs/project-state.md", "- 已完成到：M180 Desktop Beta Release Candidate\n- 未 release/tag/delete\n")
    _write(tmp_path / "docs/release/release-checklist.md", "人工确认")
    _write(tmp_path / "docs/release/update-rollback-plan.md", "回滚")
    _write(tmp_path / "docs/release/dogfood-smoke.md", "dogfood")
    for milestone in range(171, 181):
        _write(tmp_path / f"docs/exec-plans/active/{milestone}-sample.md", f"M{milestone}")
        _write(tmp_path / f"docs/decisions/{milestone}-sample.md", f"M{milestone}")
        _write(tmp_path / f"docs/phase-{milestone}-review-gate.md", f"M{milestone}")
    return tmp_path


def test_desktop_beta_ship_has_m171_to_m180_checks(tmp_path):
    project = _minimal_project(tmp_path)
    result = DesktopBetaShipService(project).review().to_dict()

    assert result["ready"] is True
    assert result["all_passed"] is True
    assert result["total"] == 10
    names = [check["name"] for check in result["checks"]]
    for milestone in range(171, 181):
        assert any(f"M{milestone}" in name for name in names)
    assert "不自动 release" in result["next_step"]


def test_desktop_beta_ship_blocks_missing_package_scripts(tmp_path):
    project = _minimal_project(tmp_path)
    (project / "apps/desktop/package.json").write_text('{"scripts":{"build":"vite build"}}', encoding="utf-8")

    result = DesktopBetaShipService(project).review().to_dict()

    assert result["ready"] is False
    assert any("M171" in failure for failure in result["p1_failures"])


def test_desktop_beta_ship_requires_publish_never(tmp_path):
    project = _minimal_project(tmp_path)
    (project / "apps/desktop/package.json").write_text(
        '{"scripts":{"build":"vite build","package:win":"electron-builder --publish always","package:win:dir":"electron-builder --dir"}}',
        encoding="utf-8",
    )

    result = DesktopBetaShipService(project).review().to_dict()

    assert result["ready"] is False
    assert any("M178" in failure for failure in result["p1_failures"])


def test_desktop_beta_ship_blocks_missing_docs_chain(tmp_path):
    project = _minimal_project(tmp_path)
    (project / "docs/phase-180-review-gate.md").unlink()

    result = DesktopBetaShipService(project).review().to_dict()

    assert result["ready"] is False
    assert any("M180" in failure for failure in result["p1_failures"])


def test_desktop_beta_ship_api_is_registered(tmp_path):
    project = _minimal_project(tmp_path)
    client = TestClient(create_app(project_dir=project))

    response = client.get("/desktop/beta-ship")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["total"] == 10
