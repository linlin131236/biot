"""Transactional task, message, and checkpoint records."""

from datetime import UTC, datetime
import json

from bolt_core.persistence.errors import PersistenceConflictError, TaskTerminalStateError
from bolt_core.persistence.models import (
    validate_identifier, validate_json_object, validate_message_content,
)

_SQLITE_INTEGER_MAX = 2**63 - 1
_TERMINAL_TASK_STATES = frozenset({"completed", "failed", "cancelled"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_nonnegative_integer(value: object) -> None:
    if type(value) is not int or not 0 <= value <= _SQLITE_INTEGER_MAX:
        raise ValueError("expected a non-negative SQLite integer")


def _validate_positive_integer(value: object) -> None:
    if type(value) is not int or not 0 < value <= _SQLITE_INTEGER_MAX:
        raise ValueError("expected a positive SQLite integer")


class TaskRecordsMixin:
    def load_task(self, task_id: str) -> dict:
        validate_identifier(task_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, workspace_id, session_id, status, revision, payload_json, "
                "created_at, updated_at from tasks where id = ?", (task_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(task_id)
        return _task_record(row)

    def list_tasks(self, workspace_id: str, statuses: list[str] | None = None) -> list[dict]:
        validate_identifier(workspace_id)
        query = (
            "select id, workspace_id, session_id, status, revision, payload_json, "
            "created_at, updated_at from tasks where workspace_id = ?"
        )
        params: list[object] = [workspace_id]
        if statuses is not None:
            for status in statuses:
                validate_identifier(status)
            query += f" and status in ({','.join('?' for _ in statuses)})"
            params.extend(statuses)
        query += " order by created_at, id"
        connection = self.database.connection()
        try:
            rows = connection.execute(query, params).fetchall()
        finally:
            connection.close()
        return [_task_record(row) for row in rows]

    def update_task(
        self, task_id: str, expected_revision: int, status: str,
        payload: dict | None = None,
    ) -> dict:
        validate_identifier(task_id)
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
            cursor = connection.execute(
                "update tasks set status = ?, payload_json = ?, revision = revision + 1, "
                "updated_at = ? where id = ? and revision = ? and revision < ?",
                (status, serialized, now, task_id, expected_revision, _SQLITE_INTEGER_MAX),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("task revision conflict")
        return self.load_task(task_id)

    def append_message(
        self, message_id: str, session_id: str, sequence: int, role: str,
        content: str, tool_call_id: str | None, metadata: dict,
    ) -> None:
        validate_identifier(message_id)
        validate_identifier(session_id)
        _validate_positive_integer(sequence)
        validate_identifier(role)
        validate_message_content(content)
        if tool_call_id is not None:
            validate_identifier(tool_call_id)
        serialized = validate_json_object(metadata)
        with self.database.transaction() as connection:
            connection.execute(
                "insert into messages(id, session_id, sequence, role, content, tool_call_id, "
                "metadata_json, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (message_id, session_id, sequence, role, content, tool_call_id, serialized, _now()),
            )

    def list_messages(self, session_id: str) -> list[dict]:
        validate_identifier(session_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, session_id, sequence, role, content, tool_call_id, metadata_json, created_at "
                "from messages where session_id = ? order by sequence", (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return [_message_record(row) for row in rows]

    def save_checkpoint(
        self, checkpoint_id: str, task_id: str, task_revision: int, payload: dict,
    ) -> None:
        validate_identifier(checkpoint_id)
        validate_identifier(task_id)
        _validate_nonnegative_integer(task_revision)
        serialized = validate_json_object(payload)
        with self.database.transaction() as connection:
            task = connection.execute("select revision from tasks where id = ?", (task_id,)).fetchone()
            if task is None:
                raise KeyError(task_id)
            if task["revision"] != task_revision:
                raise PersistenceConflictError("checkpoint task revision does not match the current task")
            connection.execute(
                "insert into checkpoints(id, task_id, task_revision, payload_json, created_at) "
                "values (?, ?, ?, ?, ?)",
                (checkpoint_id, task_id, task_revision, serialized, _now()),
            )

    def load_checkpoint(self, checkpoint_id: str) -> dict:
        validate_identifier(checkpoint_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, task_id, task_revision, payload_json, created_at from checkpoints where id = ?",
                (checkpoint_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(checkpoint_id)
        return _checkpoint_record(row)

    def list_checkpoints(self, task_id: str) -> list[dict]:
        validate_identifier(task_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, task_id, task_revision, payload_json, created_at from checkpoints "
                "where task_id = ? order by created_at, id", (task_id,),
            ).fetchall()
        finally:
            connection.close()
        return [_checkpoint_record(row) for row in rows]


def _task_record(row) -> dict:
    record = dict(row)
    record["payload"] = json.loads(record.pop("payload_json"))
    return record


def _message_record(row) -> dict:
    record = dict(row)
    record["metadata"] = json.loads(record.pop("metadata_json"))
    return record


def _checkpoint_record(row) -> dict:
    record = dict(row)
    record["payload"] = json.loads(record.pop("payload_json"))
    return record
