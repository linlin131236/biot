"""Tests for M125 public beta readiness."""
from pathlib import Path

from bolt_core.public_beta_readiness import PublicBetaReadinessService


def make_public_beta_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    for module in [
        "crash_recovery",
        "data_migration",
        "update_rollback",
        "privacy_security_audit",
        "agent_intelligence_dogfood",
        "tool_ecosystem_dogfood",
        "desktop_beta_dogfood",
        "checkpoint",
        "pause_resume",
        "session_recovery_api",
        "execution_audit_integrity",
        "thread_handoff_summary",
        "long_task_recovery_dogfood",
        "execution_audit_store",
        "context_compaction",
        "memory_permission_boundary",
        "project_profile",
        "code_map_index",
        "release_readiness",
        "local_release_checklist",
        "recovery_policy",
        "approval_apply",
        "test_runner_integration",
        "evidence_redactor",
        "tool_permission_contract",
        "readonly_tool_runner",
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    desktop = tmp_path / "apps/desktop/src"
    desktop.mkdir(parents=True, exist_ok=True)
    (desktop / "SafePanel.tsx").write_text("export const label = '安全';", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "final-handoff").mkdir(parents=True, exist_ok=True)
    (docs / "release").mkdir(parents=True, exist_ok=True)
    (docs / "references").mkdir(parents=True, exist_ok=True)
    (docs / "release/data-migration-plan.md").write_text(
        "raw staging clean lineage rollback manual approval dry-run",
        encoding="utf-8",
    )
    (docs / "release/update-rollback-plan.md").write_text(
        "manual update rollback release readiness verification approval no auto publish",
        encoding="utf-8",
    )
    (docs / "release/privacy-security-audit.md").write_text(
        "prompt injection permission secret supply chain privacy readonly",
        encoding="utf-8",
    )
    (docs / "references/anthropic-jlens-global-workspace-2026.md").write_text("只读审计", encoding="utf-8")
    (docs / "final-handoff/m125-beta-handoff.md").write_text("M55-M125 能力边界 已知风险", encoding="utf-8")
    for milestone in range(121, 126):
        (docs / f"exec-plans/active/{milestone}-beta.md").write_text(f"# M{milestone}", encoding="utf-8")
        (docs / f"decisions/{milestone}-beta.md").write_text(f"# M{milestone} decision", encoding="utf-8")
        (docs / f"phase-{milestone}-review-gate.md").write_text(f"# M{milestone} gate", encoding="utf-8")
    (docs / "project-state.md").write_text("已完成到：M125\n未 push\n未进入 M126", encoding="utf-8")
    return tmp_path


def test_public_beta_readiness_passes_for_complete_project(tmp_path):
    project = make_public_beta_project(tmp_path)
    result = PublicBetaReadinessService(str(project)).review()

    assert result.all_passed is True
    assert len(result.checks) == 10
    assert result.beta_allowed is True


def test_public_beta_readiness_fails_when_m124_missing(tmp_path):
    project = make_public_beta_project(tmp_path)
    (project / "docs/phase-124-review-gate.md").unlink()

    result = PublicBetaReadinessService(str(project)).review()

    assert result.all_passed is False
    assert result.beta_allowed is False
    assert any("M124" in item for item in result.p1_failures)


def test_public_beta_readiness_blocks_m126_boundary(tmp_path):
    project = make_public_beta_project(tmp_path)
    (project / "docs/exec-plans/active/126-next.md").write_text("# M126", encoding="utf-8")

    result = PublicBetaReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("M126" in item for item in result.p1_failures)


def test_public_beta_readiness_fails_when_child_gate_fails(tmp_path):
    project = make_public_beta_project(tmp_path)
    (project / "docs/release/data-migration-plan.md").write_text(
        "raw staging clean lineage rollback manual approval dry-run automatic migration",
        encoding="utf-8",
    )

    result = PublicBetaReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("M122" in item for item in result.p1_failures)


def test_public_beta_readiness_accepts_pushed_state_text(tmp_path):
    project = make_public_beta_project(tmp_path)
    (project / "docs/project-state.md").write_text(
        "已完成到：M125\n已 push\nHEAD = origin/main\n未进入 M126",
        encoding="utf-8",
    )

    result = PublicBetaReadinessService(str(project)).review()

    assert result.all_passed is True
