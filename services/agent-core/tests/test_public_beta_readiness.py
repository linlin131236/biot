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
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "final-handoff").mkdir(parents=True, exist_ok=True)
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
