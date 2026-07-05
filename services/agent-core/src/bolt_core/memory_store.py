from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from bolt_core.failure_memory import ToolFailure

MEMORY_KINDS = {"session", "project", "user", "tool", "failure", "long_term"}


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    kind: str
    scope: str
    content: str
    status: str
    source: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class MemoryStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path
        self._records: list[MemoryRecord] = []
        self._failures: list[ToolFailure] = []
        if db_path is not None:
            self._init_db()

    def record(self, kind: str, scope: str, content: str, source: str = "manual", tags: list[str] | None = None, metadata: dict | None = None) -> MemoryRecord:
        self._check_kind(kind)
        now = _now()
        memory = MemoryRecord(f"mem_{uuid4().hex[:12]}", kind, scope, content, "active", source, tags or [], metadata or {}, now, now)
        self._save_memory(memory)
        return memory

    def record_session(self, scope: str, content: str, source: str = "session") -> MemoryRecord:
        return self.record("session", scope, content, source)

    def record_project(self, scope: str, content: str, source: str = "project") -> MemoryRecord:
        return self.record("project", scope, content, source)

    def record_user(self, scope: str, content: str, source: str = "user") -> MemoryRecord:
        return self.record("user", scope, content, source)

    def record_tool(self, scope: str, content: str, source: str = "tool") -> MemoryRecord:
        return self.record("tool", scope, content, source)

    def record_long_term(self, scope: str, content: str, source: str = "long_term") -> MemoryRecord:
        return self.record("long_term", scope, content, source)

    def record_failure(self, failure: ToolFailure, source: str) -> MemoryRecord:
        metadata = {
            "tool": failure.tool,
            "operation": failure.operation,
            "failure_class": failure.failure_class,
            "root_cause": failure.root_cause,
            "repair_result": failure.repair_result,
        }
        memory = self.record("failure", failure.operation, failure.observable_result, source, ["failure"], metadata)
        if self.db_path is None:
            self._failures.append(failure)
        else:
            self._insert_failure(memory.id, failure)
        return memory

    def list(self, kind: str | None = None, scope: str | None = None, status: str | None = None) -> list[MemoryRecord]:
        records = self._load_records() if self.db_path is not None else self._records
        if kind is not None:
            records = [record for record in records if record.kind == kind]
        if scope is not None:
            records = [record for record in records if record.scope == scope]
        if status is not None:
            records = [record for record in records if record.status == status]
        return list(records)

    def search(self, query: str, kind: str | None = None, limit: int = 20) -> list[MemoryRecord]:
        needle = query.lower()
        records = self.list(kind=kind, status="active")
        found = [record for record in records if needle in record.content.lower()]
        return found[:limit]

    def resolve(self, memory_id: str) -> MemoryRecord:
        current = self._find(memory_id)
        updated = MemoryRecord(**{**current.__dict__, "status": "resolved", "updated_at": _now()})
        self._replace_memory(updated)
        return updated

    def snapshot(self) -> dict[str, Any]:
        return {"records": [record.__dict__ for record in self.list()], "p0_context": self.p0_context()}

    def p0_context(self) -> dict[str, list]:
        failures = self._load_failures() if self.db_path is not None else self._failures
        unresolved = [failure for failure in failures if failure.repair_result != "fixed"]
        return {"unresolved_failures": [failure.__dict__ for failure in unresolved], "hard_constraints": [self._constraint(failure) for failure in unresolved]}

    def _save_memory(self, memory: MemoryRecord) -> None:
        if self.db_path is None:
            self._records.append(memory)
        else:
            self._insert_memory(memory)

    def _replace_memory(self, memory: MemoryRecord) -> None:
        if self.db_path is None:
            self._records = [memory if record.id == memory.id else record for record in self._records]
        else:
            self._update_memory(memory)

    def _find(self, memory_id: str) -> MemoryRecord:
        for record in self.list():
            if record.id == memory_id:
                return record
        raise KeyError(memory_id)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("create table if not exists memory_records (id text primary key, kind text, scope text, content text, status text, source text, tags_json text)")
            conn.execute("create table if not exists tool_failures (memory_id text, tool text, operation text, failure_class text, observable_result text, root_cause text, repair_result text)")
            self._ensure_column(conn, "memory_records", "metadata_json", "text", "'{}'")
            self._ensure_column(conn, "memory_records", "created_at", "text", "''")
            self._ensure_column(conn, "memory_records", "updated_at", "text", "''")

    def _ensure_column(self, conn, table: str, name: str, kind: str, default: str) -> None:
        columns = [row[1] for row in conn.execute(f"pragma table_info({table})").fetchall()]
        if name not in columns:
            conn.execute(f"alter table {table} add column {name} {kind} default {default}")

    def _insert_memory(self, memory: MemoryRecord) -> None:
        with self._connect() as conn:
            conn.execute("insert into memory_records values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", _memory_row(memory))

    def _update_memory(self, memory: MemoryRecord) -> None:
        with self._connect() as conn:
            conn.execute("update memory_records set kind=?, scope=?, content=?, status=?, source=?, tags_json=?, metadata_json=?, created_at=?, updated_at=? where id=?", _update_row(memory))

    def _insert_failure(self, memory_id: str, failure: ToolFailure) -> None:
        with self._connect() as conn:
            conn.execute("insert into tool_failures values (?, ?, ?, ?, ?, ?, ?)", (memory_id, failure.tool, failure.operation, failure.failure_class, failure.observable_result, failure.root_cause, failure.repair_result))

    def _load_records(self) -> list[MemoryRecord]:
        with self._connect() as conn:
            rows = conn.execute("select id, kind, scope, content, status, source, tags_json, metadata_json, created_at, updated_at from memory_records").fetchall()
        return [MemoryRecord(row[0], row[1], row[2], row[3], row[4], row[5], json.loads(row[6]), json.loads(row[7] or "{}"), row[8], row[9]) for row in rows]

    def _load_failures(self) -> list[ToolFailure]:
        with self._connect() as conn:
            rows = conn.execute("select tool, operation, failure_class, observable_result, root_cause, repair_result from tool_failures").fetchall()
        return [ToolFailure(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        if self.db_path is None:
            raise RuntimeError("sqlite db path is not configured")
        return sqlite3.connect(self.db_path)

    def _constraint(self, failure: ToolFailure) -> str:
        return f"Do not retry {failure.operation} without changing strategy"

    def _check_kind(self, kind: str) -> None:
        if kind not in MEMORY_KINDS:
            raise ValueError(f"unknown memory kind: {kind}")


def _memory_row(memory: MemoryRecord) -> tuple:
    return (memory.id, memory.kind, memory.scope, memory.content, memory.status, memory.source, json.dumps(memory.tags), json.dumps(memory.metadata), memory.created_at, memory.updated_at)


def _update_row(memory: MemoryRecord) -> tuple:
    return (memory.kind, memory.scope, memory.content, memory.status, memory.source, json.dumps(memory.tags), json.dumps(memory.metadata), memory.created_at, memory.updated_at, memory.id)


def _now() -> str:
    return datetime.now(UTC).isoformat()
