"""Tests for M123 update and rollback readiness."""
from pathlib import Path

from bolt_core.update_rollback import UpdateRollbackReadinessService


def make_update_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    for module in [
        "release_readiness",
        "local_release_checklist",
        "recovery_policy",
        "approval_apply",
        "test_runner_integration",
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "release").mkdir(parents=True, exist_ok=True)
    (docs / "release/update-rollback-plan.md").write_text(
        "manual update rollback release readiness verification approval no auto publish",
        encoding="utf-8",
    )
    (docs / "exec-plans/active/123-update-rollback.md").write_text("# M123", encoding="utf-8")
    (docs / "decisions/123-update-rollback.md").write_text("# M123 decision", encoding="utf-8")
    (docs / "phase-123-review-gate.md").write_text("# M123 gate", encoding="utf-8")
    (docs / "project-state.md").write_text("已完成到：M123\n未进入 M124", encoding="utf-8")
    return tmp_path


def test_update_rollback_passes_for_manual_plan(tmp_path):
    project = make_update_project(tmp_path)
    result = UpdateRollbackReadinessService(str(project)).review()

    assert result.all_passed is True
    assert len(result.checks) == 9


def test_update_rollback_fails_without_release_readiness(tmp_path):
    project = make_update_project(tmp_path)
    (project / "services/agent-core/src/bolt_core/release_readiness.py").unlink()

    result = UpdateRollbackReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("发布准备" in item for item in result.p1_failures)


def test_update_rollback_blocks_auto_release_language(tmp_path):
    project = make_update_project(tmp_path)
    (project / "docs/release/update-rollback-plan.md").write_text(
        "manual update rollback approval automatic release",
        encoding="utf-8",
    )

    result = UpdateRollbackReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("自动发布" in item for item in result.p1_failures)


def test_update_rollback_fails_when_boundary_state_is_wrong(tmp_path):
    project = make_update_project(tmp_path)
    (project / "docs/project-state.md").write_text("已完成到：M124\n未进入 M125", encoding="utf-8")

    result = UpdateRollbackReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("边界" in item for item in result.p1_failures)
