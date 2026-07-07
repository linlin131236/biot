"""Tests for M121 crash recovery readiness."""
from pathlib import Path

from bolt_core.crash_recovery import CrashRecoveryService


def make_crash_recovery_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    for module in [
        "checkpoint",
        "pause_resume",
        "session_recovery_api",
        "execution_audit_integrity",
        "thread_handoff_summary",
        "long_task_recovery_dogfood",
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "exec-plans/active/121-crash-recovery.md").write_text("# M121", encoding="utf-8")
    (docs / "decisions/121-crash-recovery.md").write_text("# M121 decision", encoding="utf-8")
    (docs / "phase-121-review-gate.md").write_text("# M121 gate", encoding="utf-8")
    (docs / "project-state.md").write_text("已完成到：M121\n未进入 M122", encoding="utf-8")
    return tmp_path


def test_crash_recovery_passes_for_complete_project(tmp_path):
    project = make_crash_recovery_project(tmp_path)
    result = CrashRecoveryService(str(project)).review()

    assert result.all_passed is True
    assert len(result.checks) == 8
    assert result.p1_failures == []


def test_crash_recovery_fails_when_checkpoint_is_missing(tmp_path):
    project = make_crash_recovery_project(tmp_path)
    (project / "services/agent-core/src/bolt_core/checkpoint.py").unlink()

    result = CrashRecoveryService(str(project)).review()

    assert result.all_passed is False
    assert any("检查点" in name for name in result.p1_failures)


def test_crash_recovery_result_has_no_executable_commands(tmp_path):
    project = make_crash_recovery_project(tmp_path)
    data = CrashRecoveryService(str(project)).review().to_dict()
    serialized = str(data)

    assert "git push" not in serialized
    assert "release" not in serialized.lower()
    assert "approve_permission" not in serialized
