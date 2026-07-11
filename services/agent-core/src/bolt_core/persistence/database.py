"""Trusted SQLite database lifecycle for non-sensitive Bolt state."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import uuid4

from bolt_core.persistence.migrations import MigrationError, apply_migrations, needs_migration
from bolt_core.persistence.models import validate_backup_reason


class PersistenceState(str, Enum):
    READY = "ready"
    CORRUPT = "corrupt"
    READ_ONLY_RECOVERY = "read_only_recovery"
    FUTURE_VERSION = "future_version"
    MIGRATION_FAILED = "migration_failed"


class Database:
    def __init__(self, path: Path, state: PersistenceState) -> None:
        self.path = path
        self.state = state

    @classmethod
    def open(cls, data_root: Path) -> "Database":
        path = Path(data_root).resolve() / "state" / "bolt.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        database = cls(path, PersistenceState.READY)
        try:
            connection = database.connection()
            try:
                if database.quick_check(connection) != "ok":
                    database.state = PersistenceState.CORRUPT
                    return database
                if needs_migration(connection):
                    database.create_backup("before-migration")
                with database.transaction(connection):
                    apply_migrations(connection)
            finally:
                connection.close()
        except MigrationError as error:
            database.state = (
                PersistenceState.FUTURE_VERSION
                if "newer" in str(error)
                else PersistenceState.MIGRATION_FAILED
            )
        except RuntimeError:
            database.state = PersistenceState.MIGRATION_FAILED
        except sqlite3.DatabaseError:
            database.state = PersistenceState.CORRUPT
        return database

    def connection(self) -> sqlite3.Connection:
        if self.state is not PersistenceState.READY:
            raise RuntimeError("database is in read-only recovery")
        connection = sqlite3.connect(self.path, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("pragma foreign_keys = on")
            connection.execute("pragma journal_mode = wal")
            connection.execute("pragma busy_timeout = 5000")
            return connection
        except BaseException:
            connection.close()
            raise

    @contextmanager
    def transaction(self, connection: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
        if self.state is not PersistenceState.READY:
            raise RuntimeError("database is in read-only recovery")
        owned = connection is None
        active = connection or self.connection()
        started = False
        try:
            active.execute("begin immediate")
            started = True
            yield active
            active.execute("commit")
        except BaseException:
            if started and active.in_transaction:
                try:
                    active.execute("rollback")
                except sqlite3.DatabaseError:
                    pass
            raise
        finally:
            if owned:
                active.close()

    def create_backup(self, reason: str) -> Path:
        if self.state is not PersistenceState.READY:
            raise RuntimeError("database is in read-only recovery")
        safe_reason = validate_backup_reason(reason)
        backups = self.path.parent / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = backups / f"bolt-{safe_reason}-{stamp}-{uuid4().hex}.sqlite3"
        source = self.connection()
        destination = None
        try:
            destination = sqlite3.connect(target)
            source.backup(destination)
        finally:
            if destination is not None:
                destination.close()
            source.close()
        if self.quick_check(target) != "ok":
            target.unlink(missing_ok=True)
            raise RuntimeError("backup integrity check failed")
        return target

    def quick_check(self, connection_or_path: sqlite3.Connection | Path) -> str:
        if isinstance(connection_or_path, sqlite3.Connection):
            return str(connection_or_path.execute("pragma quick_check").fetchone()[0])
        connection = sqlite3.connect(connection_or_path)
        try:
            return str(connection.execute("pragma quick_check").fetchone()[0])
        finally:
            connection.close()

    def integrity_check(self) -> str:
        connection = self.connection()
        try:
            return str(connection.execute("pragma integrity_check").fetchone()[0])
        finally:
            connection.close()
