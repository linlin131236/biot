"""Transactional runtime task, session, and event records."""

import json

from bolt_core.persistence.errors import (
    PersistenceConflictError, TaskTerminalStateError,
    RuntimeEventSequenceError, RuntimeSessionClosedError,
)
from bolt_core.persistence.models import validate_identifier, validate_json_object
from bolt_core.persistence.task_records import (
    _SQLITE_INTEGER_MAX, _now, _validate_nonnegative_integer,
    _validate_positive_integer,
)

_CLOSED_RUNTIME_STATES = frozenset({"completed", "failed", "cancelled"})
_TERMINAL_TASK_STATES = _CLOSED_RUNTIME_STATES


class RuntimeRecordsMixin:
    def reconcile_runtime_sessions(self, workspace_id: str) -> None:
        validate_identifier(workspace_id)
        now = _now()
        with self.database.transaction() as connection:
            rows = connection.execute(
                "select rs.id, t.status from runtime_sessions rs join tasks t on t.id = rs.task_id "
                "where t.workspace_id = ? and t.status in ('completed', 'failed', 'cancelled') "
                "and rs.status not in ('completed', 'failed', 'cancelled')",
                (workspace_id,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    "update runtime_sessions set status = ?, updated_at = ? where id = ?",
                    (row["status"], now, row["id"]),
                )

    def list_runtime_tasks(
        self, workspace_id: str, statuses: list[str] | None = None,
    ) -> list[dict]:
        validate_identifier(workspace_id)
        query = (
            "select t.id, t.workspace_id, t.session_id, t.status, t.revision, t.payload_json, "
            "t.created_at, t.updated_at, rs.id as runtime_session_id from tasks t "
            "join runtime_sessions rs on rs.task_id = t.id where t.workspace_id = ?"
        )
        params: list[object] = [workspace_id]
        if statuses is not None:
            for status in statuses:
                validate_identifier(status)
            query += f" and t.status in ({','.join('?' for _ in statuses)})"
            params.extend(statuses)
        query += " order by t.created_at, t.id"
        connection = self.database.connection()
        try:
            rows = connection.execute(query, params).fetchall()
        finally:
            connection.close()
        return [_runtime_task_record(row) for row in rows]

    def create_runtime_task(
        self, task_id: str, workspace_id: str, runtime_session_id: str,
        runtime_id: str, external_session_id: str, payload: dict,
    ) -> None:
        for value in (task_id, workspace_id, runtime_session_id, runtime_id, external_session_id):
            validate_identifier(value)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into tasks(id, workspace_id, session_id, status, revision, payload_json, created_at, updated_at) "
                "values (?, ?, null, 'running', 0, ?, ?, ?)",
                (task_id, workspace_id, serialized, now, now),
            )
            connection.execute(
                "insert into runtime_sessions(id, task_id, runtime_id, external_session_id, status, created_at, updated_at) "
                "values (?, ?, ?, ?, 'running', ?, ?)",
                (runtime_session_id, task_id, runtime_id, external_session_id, now, now),
            )

    def update_runtime_task(
        self, task_id: str, runtime_session_id: str, expected_revision: int,
        status: str, payload: dict | None = None,
    ) -> dict:
        validate_identifier(task_id)
        validate_identifier(runtime_session_id)
        _validate_nonnegative_integer(expected_revision)
        validate_identifier(status)
        current = self.load_task(task_id)
        if current["revision"] != expected_revision:
            raise PersistenceConflictError("task revision conflict")
        if current["status"] in _TERMINAL_TASK_STATES:
            raise TaskTerminalStateError("task is in a terminal state")
        serialized = validate_json_object(payload if payload is not None else current["payload"])
        now = _now()
        with self.database.transaction() as connection:
            session = connection.execute(
                "select status from runtime_sessions where id = ? and task_id = ?",
                (runtime_session_id, task_id),
            ).fetchone()
            if session is None:
                raise KeyError(runtime_session_id)
            if session["status"] in _CLOSED_RUNTIME_STATES and status not in _CLOSED_RUNTIME_STATES:
                raise RuntimeSessionClosedError("runtime session is closed")
            cursor = connection.execute(
                "update tasks set status = ?, payload_json = ?, revision = revision + 1, "
                "updated_at = ? where id = ? and revision = ? and revision < ?",
                (status, serialized, now, task_id, expected_revision, _SQLITE_INTEGER_MAX),
            )
            if cursor.rowcount != 1:
                raise PersistenceConflictError("task revision conflict")
            connection.execute(
                "update runtime_sessions set status = ?, updated_at = ? where id = ?",
                (status, now, runtime_session_id),
            )
        return self.load_task(task_id)

    def create_runtime_session(
        self, runtime_session_id: str, task_id: str, runtime_id: str,
        external_session_id: str, status: str,
    ) -> None:
        for value in (runtime_session_id, task_id, runtime_id, external_session_id, status):
            validate_identifier(value)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into runtime_sessions(id, task_id, runtime_id, external_session_id, status, created_at, updated_at) "
                "values (?, ?, ?, ?, ?, ?, ?)",
                (runtime_session_id, task_id, runtime_id, external_session_id, status, now, now),
            )

    def append_runtime_event(
        self, event_id: str, runtime_session_id: str, sequence: int,
        event_type: str, payload: dict,
    ) -> None:
        validate_identifier(event_id)
        validate_identifier(runtime_session_id)
        _validate_positive_integer(sequence)
        validate_identifier(event_type)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            session = connection.execute(
                "select status from runtime_sessions where id = ?", (runtime_session_id,),
            ).fetchone()
            if session is None or session["status"] in _CLOSED_RUNTIME_STATES:
                raise RuntimeSessionClosedError("runtime session is closed")
            last = connection.execute(
                "select max(sequence) as last_sequence from runtime_events where runtime_session_id = ?",
                (runtime_session_id,),
            ).fetchone()["last_sequence"]
            if sequence != (1 if last is None else last + 1):
                raise RuntimeEventSequenceError(
                    "runtime event sequence must be strictly monotonic and gapless"
                )
            connection.execute(
                "insert into runtime_events(id, runtime_session_id, sequence, type, payload_json, created_at) "
                "values (?, ?, ?, ?, ?, ?)",
                (event_id, runtime_session_id, sequence, event_type, serialized, now),
            )

    def append_runtime_event_with_status(
        self, event_id: str, runtime_session_id: str, sequence: int,
        event_type: str, payload: dict, status: str,
    ) -> None:
        validate_identifier(event_id)
        validate_identifier(runtime_session_id)
        _validate_positive_integer(sequence)
        validate_identifier(event_type)
        validate_identifier(status)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            row = connection.execute(
                "select rs.status, rs.task_id, t.status as task_status from runtime_sessions rs "
                "join tasks t on t.id = rs.task_id where rs.id = ?",
                (runtime_session_id,),
            ).fetchone()
            if row is None or row["status"] in _CLOSED_RUNTIME_STATES:
                raise RuntimeSessionClosedError("runtime session is closed")
            if row["task_status"] in _TERMINAL_TASK_STATES:
                raise TaskTerminalStateError("task is in a terminal state")
            last = connection.execute(
                "select max(sequence) as last_sequence from runtime_events where runtime_session_id = ?",
                (runtime_session_id,),
            ).fetchone()["last_sequence"]
            if sequence != (1 if last is None else last + 1):
                raise RuntimeEventSequenceError(
                    "runtime event sequence must be strictly monotonic and gapless"
                )
            connection.execute(
                "insert into runtime_events(id, runtime_session_id, sequence, type, payload_json, created_at) "
                "values (?, ?, ?, ?, ?, ?)",
                (event_id, runtime_session_id, sequence, event_type, serialized, now),
            )
            connection.execute(
                "update runtime_sessions set status = ?, updated_at = ? where id = ?",
                (status, now, runtime_session_id),
            )
            connection.execute(
                "update tasks set status = ?, revision = revision + 1, updated_at = ? where id = ?",
                (status, now, row["task_id"]),
            )

    def runtime_session_is_open(self, runtime_session_id: str) -> bool:
        validate_identifier(runtime_session_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select status from runtime_sessions where id = ?", (runtime_session_id,),
            ).fetchone()
        finally:
            connection.close()
        return row is not None and row["status"] not in _CLOSED_RUNTIME_STATES

    def set_runtime_session_status(self, runtime_session_id: str, status: str) -> None:
        validate_identifier(runtime_session_id)
        validate_identifier(status)
        if status in _CLOSED_RUNTIME_STATES:
            self.close_runtime_session(runtime_session_id, status)
            return
        self._set_open_runtime_session_status(runtime_session_id, status)

    def close_runtime_session(self, runtime_session_id: str, status: str) -> None:
        validate_identifier(runtime_session_id)
        validate_identifier(status)
        if status not in _CLOSED_RUNTIME_STATES:
            raise ValueError("runtime session close requires a terminal status")
        self._set_open_runtime_session_status(runtime_session_id, status)

    def list_runtime_sessions(self, workspace_id: str) -> list[dict]:
        validate_identifier(workspace_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select rs.id, rs.task_id, rs.runtime_id, rs.external_session_id, rs.status, "
                "rs.created_at, rs.updated_at, t.payload_json from runtime_sessions rs "
                "join tasks t on t.id = rs.task_id where t.workspace_id = ? "
                "order by rs.created_at, rs.id",
                (workspace_id,),
            ).fetchall()
        finally:
            connection.close()
        return [_runtime_session_record(row) for row in rows]

    def list_runtime_events(self, runtime_session_id: str) -> list[dict]:
        validate_identifier(runtime_session_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, runtime_session_id, sequence, type, payload_json, created_at "
                "from runtime_events where runtime_session_id = ? order by sequence",
                (runtime_session_id,),
            ).fetchall()
        finally:
            connection.close()
        return [_runtime_event_record(row) for row in rows]

    def _set_open_runtime_session_status(self, runtime_session_id: str, status: str) -> None:
        now = _now()
        with self.database.transaction() as connection:
            current = connection.execute(
                "select status from runtime_sessions where id = ?", (runtime_session_id,),
            ).fetchone()
            if current is None:
                raise KeyError(runtime_session_id)
            if current["status"] in _CLOSED_RUNTIME_STATES:
                raise RuntimeSessionClosedError("runtime session is closed")
            connection.execute(
                "update runtime_sessions set status = ?, updated_at = ? where id = ?",
                (status, now, runtime_session_id),
            )


def _runtime_task_record(row) -> dict:
    record = dict(row)
    record["payload"] = json.loads(record.pop("payload_json"))
    return record


def _runtime_session_record(row) -> dict:
    record = dict(row)
    record["task_payload"] = json.loads(record.pop("payload_json"))
    return record


def _runtime_event_record(row) -> dict:
    record = dict(row)
    record["payload"] = json.loads(record.pop("payload_json"))
    return record
