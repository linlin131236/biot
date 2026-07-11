from pathlib import Path
import sqlite3
import threading
import time

import pytest

from bolt_core.persistence.database import Database, PersistenceState


def test_database_uses_only_trusted_data_root(tmp_path):
    data_root = tmp_path / "electron-user-data"

    database = Database.open(data_root)

    assert database.path == data_root / "state" / "bolt.sqlite3"
    assert database.state is PersistenceState.READY
    assert database.path.exists()


def test_database_enables_wal_foreign_keys_and_busy_timeout(tmp_path):
    database = Database.open(tmp_path / "user-data")

    with database.connection() as connection:
        assert connection.execute("pragma journal_mode").fetchone()[0].lower() == "wal"
        assert connection.execute("pragma foreign_keys").fetchone()[0] == 1
        assert connection.execute("pragma busy_timeout").fetchone()[0] > 0


def test_connection_closes_when_pragma_initialization_fails(tmp_path, monkeypatch):
    closed = False

    class Connection:
        row_factory = None

        def execute(self, _):
            raise sqlite3.OperationalError("pragma failure")

        def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: Connection())

    database = Database.open(tmp_path / "user-data")

    assert database.state is PersistenceState.CORRUPT
    assert closed


def test_database_open_releases_its_connection_for_windows_rename(tmp_path):
    database = Database.open(tmp_path / "user-data")
    renamed = database.path.with_name("renamed.sqlite3")

    database.path.rename(renamed)

    assert renamed.exists()


def test_database_transaction_rolls_back_all_rows_on_error(tmp_path):
    database = Database.open(tmp_path / "user-data")

    with pytest.raises(RuntimeError, match="abort"):
        with database.transaction() as connection:
            connection.execute(
                "insert into workspaces(workspace_id, canonical_path, created_at, updated_at, revision) values (?, ?, ?, ?, ?)",
                ("workspace.v1.one", "C:/workspace", "2026-07-11T00:00:00+00:00", "2026-07-11T00:00:00+00:00", 0),
            )
            raise RuntimeError("abort")

    with database.connection() as connection:
        assert connection.execute("select count(*) from workspaces").fetchone()[0] == 0


def test_database_creates_verified_backup_before_migration(tmp_path):
    database = Database.open(tmp_path / "user-data")

    backup = database.create_backup("before-test")

    assert backup.parent == database.path.parent / "backups"
    assert backup.exists()
    assert database.quick_check(backup) == "ok"


def test_backup_reason_rejects_secret_without_creating_filename(tmp_path):
    database = Database.open(tmp_path / "user-data")
    secret = "sk-C4N4RY7D83CBB5XX"
    backups = database.path.parent / "backups"
    before = {path.name for path in backups.glob("*.sqlite3")}

    with pytest.raises(ValueError):
        database.create_backup(f"manual-{secret}")

    assert {path.name for path in backups.glob("*.sqlite3")} == before


def test_backup_releases_source_connection_for_windows_rename(tmp_path):
    database = Database.open(tmp_path / "user-data")
    database.create_backup("manual")
    renamed = database.path.with_name("renamed.sqlite3")

    database.path.rename(renamed)

    assert renamed.exists()


def test_backup_closes_source_when_destination_connection_fails(tmp_path, monkeypatch):
    database = Database.open(tmp_path / "user-data")
    closed = False

    class Source:
        def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(database, "connection", lambda: Source())
    monkeypatch.setattr(
        sqlite3, "connect", lambda _: (_ for _ in ()).throw(sqlite3.OperationalError("blocked")),
    )

    with pytest.raises(sqlite3.OperationalError, match="blocked"):
        database.create_backup("destination-failure")
    assert closed


def test_path_quick_check_explicitly_closes_its_connection(tmp_path, monkeypatch):
    database = Database.open(tmp_path / "user-data")
    closed = False

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):
            return self

        def fetchone(self):
            return ("ok",)

        def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(sqlite3, "connect", lambda _: Connection())

    assert database.quick_check(database.path) == "ok"
    assert closed


def test_integrity_check_explicitly_closes_its_connection(tmp_path, monkeypatch):
    database = Database.open(tmp_path / "user-data")
    closed = False

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):
            return self

        def fetchone(self):
            return ("ok",)

        def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(database, "connection", lambda: Connection())

    assert database.integrity_check() == "ok"
    assert closed


def test_database_refuses_a_corrupt_file_without_overwriting_it(tmp_path):
    data_root = tmp_path / "user-data"
    db_path = data_root / "state" / "bolt.sqlite3"
    db_path.parent.mkdir(parents=True)
    original = b"not a sqlite database"
    db_path.write_bytes(original)

    database = Database.open(data_root)

    assert database.state is PersistenceState.CORRUPT
    assert db_path.read_bytes() == original
    with pytest.raises(RuntimeError, match="read-only recovery"):
        with database.transaction():
            pass


def test_backups_created_in_the_same_second_never_overwrite_each_other(tmp_path):
    database = Database.open(tmp_path / "user-data")

    first = database.create_backup("manual")
    second = database.create_backup("manual")

    assert first != second
    assert first.exists()
    assert second.exists()


def test_second_writer_waits_for_committed_transaction_without_losing_its_write(tmp_path):
    database = Database.open(tmp_path / "user-data")
    started = threading.Event()
    completed = threading.Event()
    failures: list[BaseException] = []

    def write_after_lock_releases() -> None:
        try:
            started.set()
            with database.transaction() as connection:
                connection.execute(
                    "insert into workspaces(workspace_id, canonical_path, created_at, updated_at, revision) values (?, ?, ?, ?, ?)",
                    ("workspace.v1.second", "C:/second", "now", "now", 0),
                )
        except BaseException as error:
            failures.append(error)
        finally:
            completed.set()

    with database.transaction() as connection:
        connection.execute(
            "insert into workspaces(workspace_id, canonical_path, created_at, updated_at, revision) values (?, ?, ?, ?, ?)",
            ("workspace.v1.first", "C:/first", "now", "now", 0),
        )
        worker = threading.Thread(target=write_after_lock_releases)
        worker.start()
        assert started.wait(timeout=1)
        time.sleep(0.05)
        assert not completed.is_set()

    worker.join(timeout=2)
    assert not failures
    assert completed.is_set()
    with database.connection() as connection:
        assert connection.execute("select count(*) from workspaces").fetchone()[0] == 2


def test_database_transaction_preserves_begin_immediate_lock_error(tmp_path):
    database = Database.open(tmp_path / "user-data")
    holder = database.connection()
    contender = database.connection()
    contender.execute("pragma busy_timeout = 1")
    holder.execute("begin immediate")

    try:
        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            with database.transaction(contender):
                pass
    finally:
        holder.execute("rollback")
        contender.close()
        holder.close()


def test_integrity_check_returns_sqlite_diagnostic(tmp_path):
    database = Database.open(tmp_path / "user-data")

    assert database.integrity_check() == "ok"
