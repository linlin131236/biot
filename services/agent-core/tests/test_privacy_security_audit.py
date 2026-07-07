"""Tests for M124 privacy and security audit readiness."""
from pathlib import Path

from bolt_core.privacy_security_audit import PrivacySecurityAuditService


def make_privacy_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    for module in [
        "evidence_redactor",
        "memory_permission_boundary",
        "tool_permission_contract",
        "approval_apply",
        "readonly_tool_runner",
        "agent_intelligence_dogfood",
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    desktop = tmp_path / "apps/desktop/src"
    desktop.mkdir(parents=True, exist_ok=True)
    (desktop / "SafePanel.tsx").write_text("export const label = '安全';", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "references").mkdir(parents=True, exist_ok=True)
    (docs / "release").mkdir(parents=True, exist_ok=True)
    (docs / "references/anthropic-jlens-global-workspace-2026.md").write_text("只读审计", encoding="utf-8")
    (docs / "release/privacy-security-audit.md").write_text(
        "prompt injection permission secret token cert supply chain privacy readonly audit",
        encoding="utf-8",
    )
    (docs / "exec-plans/active/124-privacy-security-audit.md").write_text("# M124", encoding="utf-8")
    (docs / "decisions/124-privacy-security-audit.md").write_text("# M124 decision", encoding="utf-8")
    (docs / "phase-124-review-gate.md").write_text("# M124 gate", encoding="utf-8")
    (docs / "project-state.md").write_text("已完成到：M124\n未进入 M125", encoding="utf-8")
    return tmp_path


def test_privacy_security_audit_passes_for_complete_project(tmp_path):
    project = make_privacy_project(tmp_path)
    result = PrivacySecurityAuditService(str(project)).review()

    assert result.all_passed is True
    assert len(result.checks) == 9


def test_privacy_security_audit_fails_on_renderer_exposure(tmp_path):
    project = make_privacy_project(tmp_path)
    (project / "apps/desktop/src/SafePanel.tsx").write_text("console.log(process.env.SECRET)", encoding="utf-8")

    result = PrivacySecurityAuditService(str(project)).review()

    assert result.all_passed is False
    assert any("renderer" in item.lower() for item in result.p1_failures)


def test_privacy_security_audit_fails_on_type_escape(tmp_path):
    project = make_privacy_project(tmp_path)
    (project / "apps/desktop/src/SafePanel.tsx").write_text("const value = input as any;", encoding="utf-8")

    result = PrivacySecurityAuditService(str(project)).review()

    assert result.all_passed is False
    assert any("as any" in item for item in result.p1_failures)
