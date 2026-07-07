"""Tests for M122 data migration readiness."""
from pathlib import Path

from bolt_core.data_migration import DataMigrationReadinessService


def make_data_migration_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    for module in [
        "execution_audit_store",
        "context_compaction",
        "thread_handoff_summary",
        "memory_permission_boundary",
        "project_profile",
        "code_map_index",
    ]:
        (src / f"{module}.py").write_text(f"# {module}", encoding="utf-8")

    docs = tmp_path / "docs"
    (docs / "exec-plans/active").mkdir(parents=True, exist_ok=True)
    (docs / "decisions").mkdir(parents=True, exist_ok=True)
    (docs / "release").mkdir(parents=True, exist_ok=True)
    (docs / "release/data-migration-plan.md").write_text(
        "raw staging clean lineage rollback manual approval dry-run",
        encoding="utf-8",
    )
    (docs / "exec-plans/active/122-data-migration.md").write_text("# M122", encoding="utf-8")
    (docs / "decisions/122-data-migration.md").write_text("# M122 decision", encoding="utf-8")
    (docs / "phase-122-review-gate.md").write_text("# M122 gate", encoding="utf-8")
    (docs / "project-state.md").write_text("已完成到：M122\n未进入 M123", encoding="utf-8")
    return tmp_path


def test_data_migration_passes_with_manifest_and_lineage(tmp_path):
    project = make_data_migration_project(tmp_path)
    result = DataMigrationReadinessService(str(project)).review()

    assert result.all_passed is True
    assert len(result.checks) == 8


def test_data_migration_fails_without_rollback_plan(tmp_path):
    project = make_data_migration_project(tmp_path)
    (project / "docs/release/data-migration-plan.md").write_text("raw staging clean lineage", encoding="utf-8")

    result = DataMigrationReadinessService(str(project)).review()

    assert result.all_passed is False
    assert any("回滚" in item for item in result.p1_failures)


def test_data_migration_is_plan_only_not_auto_apply(tmp_path):
    project = make_data_migration_project(tmp_path)
    service_text = "dry-run only; no auto migration"
    (project / "services/agent-core/src/bolt_core/data_migration.py").write_text(service_text, encoding="utf-8")

    result = DataMigrationReadinessService(str(project)).review()

    assert result.all_passed is True
    assert "自动迁移" not in str(result.to_dict())
