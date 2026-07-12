"""Immutable schema migrations for Bolt's non-sensitive control-plane database."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
from inspect import getsource
import sqlite3
from typing import Callable


class MigrationError(RuntimeError):
    """A schema ledger or migration operation is unsafe to continue."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]
    schema: tuple[str, ...] = ()

    @cached_property
    def checksum(self) -> str:
        material = "\n".join((
            str(self.version), self.name, _apply_source(self.apply), *self.schema,
        ))
        return sha256(material.encode("utf-8")).hexdigest()


def _apply_source(apply: Callable[[sqlite3.Connection], None]) -> str:
    try:
        return getsource(apply)
    except (OSError, TypeError):
        code = apply.__code__
        return f"{code.co_code.hex()}:{code.co_consts!r}"


def apply_migrations(connection: sqlite3.Connection) -> None:
    applied = _applied_migrations(connection)
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        migration.apply(connection)
        connection.execute(
            "insert into schema_migrations(version, applied_at, checksum) values (?, datetime('now'), ?)",
            (migration.version, migration.checksum),
        )


def needs_migration(connection: sqlite3.Connection) -> bool:
    applied = _applied_migrations(connection, create_ledger=False)
    return any(migration.version not in applied for migration in MIGRATIONS)


def _applied_migrations(
    connection: sqlite3.Connection, *, create_ledger: bool = True
) -> dict[int, str]:
    if create_ledger:
        connection.execute(
            "create table if not exists schema_migrations ("
            "version integer primary key, applied_at text not null, checksum text not null)"
        )
    elif not _table_exists(connection, "schema_migrations"):
        return {}
    applied = {
        int(row["version"]): str(row["checksum"])
        for row in connection.execute("select version, checksum from schema_migrations")
    }
    latest = MIGRATIONS[-1].version
    if any(version > latest for version in applied):
        raise MigrationError("database schema is newer than this Bolt version")
    for migration in MIGRATIONS:
        recorded = applied.get(migration.version)
        if recorded is not None and recorded != migration.checksum:
            raise MigrationError("migration checksum mismatch")
    return applied


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "select 1 from sqlite_master where type = 'table' and name = ?", (name,)
    ).fetchone() is not None


_V1_SCHEMA = (
    """create table workspaces (
            workspace_id text primary key,
            canonical_path text not null unique,
            created_at text not null,
            updated_at text not null,
            revision integer not null
        )""",
        """create table sessions (
            id text primary key,
            workspace_id text not null references workspaces(workspace_id) on delete restrict,
            status text not null,
            created_at text not null,
            updated_at text not null
        )""",
        """create table messages (
            id text primary key,
            session_id text not null references sessions(id) on delete restrict,
            sequence integer not null,
            role text not null,
            content text not null,
            tool_call_id text,
            metadata_json text not null,
            created_at text not null,
            unique(session_id, sequence)
        )""",
        """create table tasks (
            id text primary key,
            workspace_id text not null references workspaces(workspace_id) on delete restrict,
            session_id text references sessions(id) on delete restrict,
            status text not null,
            revision integer not null,
            payload_json text not null,
            created_at text not null,
            updated_at text not null
        )""",
        """create table runtime_sessions (
            id text primary key,
            task_id text not null references tasks(id) on delete restrict,
            runtime_id text not null,
            external_session_id text not null,
            status text not null,
            created_at text not null,
            updated_at text not null,
            unique(task_id, runtime_id, external_session_id)
        )""",
        """create table runtime_events (
            id text primary key,
            runtime_session_id text not null references runtime_sessions(id) on delete restrict,
            sequence integer not null,
            type text not null,
            payload_json text not null,
            created_at text not null,
            unique(runtime_session_id, sequence)
        )""",
        """create table checkpoints (
            id text primary key,
            task_id text not null references tasks(id) on delete restrict,
            task_revision integer not null,
            payload_json text not null,
            created_at text not null
        )""",
    """create table model_profiles (
            id text primary key,
            workspace_id text references workspaces(workspace_id) on delete restrict,
            provider text not null,
            base_url text not null,
            model text not null,
            temperature real not null,
            timeout real not null,
            context_window integer not null,
            credential_id text,
            revision integer not null,
            config_json text not null,
            created_at text not null,
            updated_at text not null
        )""",
)


def _create_v1_schema(connection: sqlite3.Connection) -> None:
    for statement in _V1_SCHEMA:
        connection.execute(statement)


_V2_SCHEMA = (
    """create table task_closures (
            id text primary key,
            workspace_id text not null references workspaces(workspace_id) on delete restrict,
            status text not null,
            revision integer not null,
            payload_json text not null,
            created_at text not null,
            updated_at text not null
        )""",
)


def _create_v2_schema(connection: sqlite3.Connection) -> None:
    for statement in _V2_SCHEMA:
        connection.execute(statement)


_V3_SCHEMA = (
    """create table execution_queue_items (
            id text primary key,
            workspace_id text not null references workspaces(workspace_id) on delete restrict,
            status text not null,
            revision integer not null,
            payload_json text not null,
            created_at text not null,
            updated_at text not null
        )""",
)


def _create_v3_schema(connection: sqlite3.Connection) -> None:
    for statement in _V3_SCHEMA:
        connection.execute(statement)


_V4_SCHEMA = (
    """create table execution_handoffs (
            id text primary key,
            workspace_id text not null references workspaces(workspace_id) on delete restrict,
            queue_item_id text not null references execution_queue_items(id) on delete restrict,
            closure_id text not null references task_closures(id) on delete restrict,
            status text not null,
            revision integer not null,
            payload_json text not null,
            created_at text not null,
            updated_at text not null
        )""",
)


def _create_v4_schema(connection: sqlite3.Connection) -> None:
    for statement in _V4_SCHEMA:
        connection.execute(statement)


MIGRATIONS = (
    Migration(1, "initial_control_plane", _create_v1_schema, _V1_SCHEMA),
    Migration(2, "task_closures", _create_v2_schema, _V2_SCHEMA),
    Migration(3, "execution_queue_items", _create_v3_schema, _V3_SCHEMA),
    Migration(4, "execution_handoffs", _create_v4_schema, _V4_SCHEMA),
)
