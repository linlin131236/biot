import shutil
import sqlite3
from pathlib import Path

import pytest

from bolt_core.persistence import migrations
from bolt_core.persistence.database import Database, PersistenceState
from bolt_core.persistence.migrations import MIGRATIONS, Migration

_FIXTURE = Path(__file__).parent / "fixtures" / "persistence" / "v0-empty.sqlite3"


def test_empty_database_migrates_to_v1_with_required_tables(tmp_path):
    database = Database.open(tmp_path / "user-data")

    with database.connection() as connection:
        tables = {
            row[0] for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }
        versions = connection.execute(
            "select version, checksum from schema_migrations"
        ).fetchall()

    assert tables >= {
        "schema_migrations", "workspaces", "sessions", "messages", "tasks",
        "runtime_sessions", "runtime_events", "checkpoints", "model_profiles",
    }
    assert [(row[0], row[1]) for row in versions] == [(1, MIGRATIONS[0].checksum)]


def test_empty_v0_fixture_upgrades_to_v1(tmp_path):
    data_root = tmp_path / "user-data"
    target = data_root / "state" / "bolt.sqlite3"
    target.parent.mkdir(parents=True)
    shutil.copyfile(_FIXTURE, target)

    database = Database.open(data_root)

    assert database.state is PersistenceState.READY
    with database.connection() as connection:
        assert connection.execute("select version from schema_migrations").fetchone()[0] == 1
        assert connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'model_profiles'"
        ).fetchone() is not None


def test_reopening_database_does_not_repeat_migration_or_change_ledger(tmp_path):
    root = tmp_path / "user-data"
    first = Database.open(root)
    with first.connection() as connection:
        before = connection.execute("select version, checksum from schema_migrations").fetchall()

    second = Database.open(root)
    with second.connection() as connection:
        after = connection.execute("select version, checksum from schema_migrations").fetchall()

    assert [(row[0], row[1]) for row in before] == [(row[0], row[1]) for row in after]


def test_future_schema_version_enters_read_only_recovery(tmp_path):
    root = tmp_path / "user-data"
    database = Database.open(root)
    with database.transaction() as connection:
        connection.execute(
            "insert into schema_migrations(version, applied_at, checksum) values (?, ?, ?)",
            (99, "2026-07-11T00:00:00+00:00", "future"),
        )

    recovered = Database.open(root)

    assert recovered.state is PersistenceState.FUTURE_VERSION
    with pytest.raises(RuntimeError, match="read-only recovery"):
        recovered.connection()


def test_checksum_mismatch_enters_read_only_recovery(tmp_path):
    root = tmp_path / "user-data"
    database = Database.open(root)
    with database.transaction() as connection:
        connection.execute("update schema_migrations set checksum = 'tampered' where version = 1")

    recovered = Database.open(root)

    assert recovered.state is PersistenceState.MIGRATION_FAILED


def test_migration_checksum_changes_when_apply_schema_content_changes():
    def create_first_schema(connection):
        connection.execute("create table first_schema (id text primary key)")

    def create_second_schema(connection):
        connection.execute("create table second_schema (id text primary key)")

    first = Migration(1, "same_migration", create_first_schema)
    second = Migration(1, "same_migration", create_second_schema)

    assert first.checksum != second.checksum


def test_open_detects_tampered_actual_migration_content(tmp_path):
    root = tmp_path / "user-data"
    Database.open(root)
    original_migrations = migrations.MIGRATIONS

    def tampered_initial_schema(connection):
        connection.execute("create table tampered_schema (id text primary key)")

    migrations.MIGRATIONS = (
        Migration(1, "initial_control_plane", tampered_initial_schema),
    )
    try:
        recovered = Database.open(root)
    finally:
        migrations.MIGRATIONS = original_migrations

    assert recovered.state is PersistenceState.MIGRATION_FAILED


def test_migration_preflight_creates_consistent_backup(tmp_path):
    root = tmp_path / "user-data"

    database = Database.open(root)

    backups = list((database.path.parent / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("pragma quick_check").fetchone()[0] == "ok"


def test_failed_migration_rolls_back_ledger_and_preserves_backup(tmp_path, monkeypatch):
    root = tmp_path / "user-data"

    def fail_after_schema_write(connection):
        connection.execute("create table partial_schema (id text primary key)")
        raise RuntimeError("migration interrupted")

    monkeypatch.setattr(migrations, "MIGRATIONS", (Migration(1, "fails", fail_after_schema_write),))

    database = Database.open(root)

    assert database.state is PersistenceState.MIGRATION_FAILED
    assert list((database.path.parent / "backups").glob("*.sqlite3"))
    with sqlite3.connect(database.path) as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type = 'table'")}
    assert "schema_migrations" not in tables
    assert "partial_schema" not in tables
