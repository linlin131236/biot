"""Transactional closure, queue, and handoff records."""

from datetime import UTC, datetime
import json

from bolt_core.persistence.errors import PersistenceConflictError
from bolt_core.persistence.models import validate_identifier, validate_json_object

_SQLITE_INTEGER_MAX = 2**63 - 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_nonnegative_integer(value: object) -> None:
    if type(value) is not int or not 0 <= value <= _SQLITE_INTEGER_MAX:
        raise ValueError("expected a non-negative SQLite integer")


class ExecutionRecordsMixin:
    def create_closure(
        self, closure_id: str, workspace_id: str, status: str, payload: dict,
    ) -> None:
        validate_identifier(closure_id)
        validate_identifier(workspace_id)
        validate_identifier(status)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into task_closures(id, workspace_id, status, revision, payload_json, "
                "created_at, updated_at) values (?, ?, ?, 0, ?, ?, ?)",
                (closure_id, workspace_id, status, serialized, now, now),
            )

    def load_closure(self, closure_id: str) -> dict:
        validate_identifier(closure_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, workspace_id, status, revision, payload_json, created_at, updated_at "
                "from task_closures where id = ?",
                (closure_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(closure_id)
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def list_closures(self, workspace_id: str) -> list[dict]:
        validate_identifier(workspace_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, workspace_id, status, revision, payload_json, created_at, updated_at "
                "from task_closures where workspace_id = ? order by created_at, id",
                (workspace_id,),
            ).fetchall()
        finally:
            connection.close()
        results = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record.pop("payload_json"))
            results.append(record)
        return results

    def update_closure(
        self, closure_id: str, expected_revision: int, status: str,
        payload: dict | None = None,
    ) -> dict:
        validate_identifier(closure_id)
        _validate_nonnegative_integer(expected_revision)
        validate_identifier(status)
        current = self.load_closure(closure_id)
        if current["revision"] != expected_revision:
            raise PersistenceConflictError("closure revision conflict")
        serialized = (
            validate_json_object(payload) if payload is not None
            else validate_json_object(current["payload"])
        )
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "update task_closures set status = ?, payload_json = ?, revision = revision + 1, "
                "updated_at = ? where id = ? and revision = ? and revision < ?",
                (status, serialized, now, closure_id, expected_revision, _SQLITE_INTEGER_MAX),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("closure revision conflict")
        return self.load_closure(closure_id)

    def create_queue_item(
        self, item_id: str, workspace_id: str, status: str, payload: dict,
    ) -> None:
        validate_identifier(item_id)
        validate_identifier(workspace_id)
        validate_identifier(status)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into execution_queue_items(id, workspace_id, status, revision, "
                "payload_json, created_at, updated_at) values (?, ?, ?, 0, ?, ?, ?)",
                (item_id, workspace_id, status, serialized, now, now),
            )

    def load_queue_item(self, item_id: str) -> dict:
        validate_identifier(item_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, workspace_id, status, revision, payload_json, created_at, updated_at "
                "from execution_queue_items where id = ?",
                (item_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(item_id)
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def list_queue_items(self, workspace_id: str) -> list[dict]:
        validate_identifier(workspace_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, workspace_id, status, revision, payload_json, created_at, updated_at "
                "from execution_queue_items where workspace_id = ? order by created_at, id",
                (workspace_id,),
            ).fetchall()
        finally:
            connection.close()
        results = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record.pop("payload_json"))
            results.append(record)
        return results

    def update_queue_item(
        self, item_id: str, expected_revision: int, status: str,
        payload: dict | None = None,
    ) -> dict:
        validate_identifier(item_id)
        _validate_nonnegative_integer(expected_revision)
        validate_identifier(status)
        current = self.load_queue_item(item_id)
        if current["revision"] != expected_revision:
            raise PersistenceConflictError("queue item revision conflict")
        serialized = (
            validate_json_object(payload) if payload is not None
            else validate_json_object(current["payload"])
        )
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "update execution_queue_items set status = ?, payload_json = ?, "
                "revision = revision + 1, updated_at = ? "
                "where id = ? and revision = ? and revision < ?",
                (status, serialized, now, item_id, expected_revision, _SQLITE_INTEGER_MAX),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("queue item revision conflict")
        return self.load_queue_item(item_id)

    def create_handoff_record(
        self, record_id: str, workspace_id: str, queue_item_id: str,
        closure_id: str, status: str, payload: dict,
    ) -> None:
        validate_identifier(record_id)
        validate_identifier(workspace_id)
        validate_identifier(queue_item_id)
        validate_identifier(closure_id)
        validate_identifier(status)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            queue = connection.execute(
                "select workspace_id from execution_queue_items where id = ?",
                (queue_item_id,),
            ).fetchone()
            closure = connection.execute(
                "select workspace_id from task_closures where id = ?",
                (closure_id,),
            ).fetchone()
            if queue is None or closure is None:
                raise ValueError("handoff references missing execution state")
            if queue["workspace_id"] != workspace_id or closure["workspace_id"] != workspace_id:
                raise ValueError("handoff workspace mismatch")
            connection.execute(
                "insert into execution_handoffs(id, workspace_id, queue_item_id, closure_id, status, revision, "
                "payload_json, created_at, updated_at) values (?, ?, ?, ?, ?, 0, ?, ?, ?)",
                (record_id, workspace_id, queue_item_id, closure_id, status, serialized, now, now),
            )

    def load_handoff_record(self, record_id: str) -> dict:
        validate_identifier(record_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, workspace_id, queue_item_id, closure_id, status, revision, payload_json, "
                "created_at, updated_at from execution_handoffs where id = ?",
                (record_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(record_id)
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def list_handoff_records(self, workspace_id: str) -> list[dict]:
        validate_identifier(workspace_id)
        connection = self.database.connection()
        try:
            rows = connection.execute(
                "select id, workspace_id, queue_item_id, closure_id, status, revision, payload_json, "
                "created_at, updated_at from execution_handoffs where workspace_id = ? order by created_at, id",
                (workspace_id,),
            ).fetchall()
        finally:
            connection.close()
        results = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record.pop("payload_json"))
            results.append(record)
        return results

    def update_handoff_record(
        self, record_id: str, expected_revision: int, status: str,
        payload: dict | None = None,
    ) -> dict:
        validate_identifier(record_id)
        _validate_nonnegative_integer(expected_revision)
        validate_identifier(status)
        current = self.load_handoff_record(record_id)
        if current["revision"] != expected_revision:
            raise PersistenceConflictError("handoff revision conflict")
        serialized = (
            validate_json_object(payload) if payload is not None
            else validate_json_object(current["payload"])
        )
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "update execution_handoffs set status = ?, payload_json = ?, revision = revision + 1, "
                "updated_at = ? where id = ? and revision = ? and revision < ?",
                (status, serialized, now, record_id, expected_revision, _SQLITE_INTEGER_MAX),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("handoff revision conflict")
        return self.load_handoff_record(record_id)
