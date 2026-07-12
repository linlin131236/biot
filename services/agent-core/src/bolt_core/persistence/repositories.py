"""Transactional repositories for non-sensitive Bolt control-plane records."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import math
from pathlib import Path
import sqlite3

from bolt_core.desktop_runner import stable_workspace_identity
from bolt_core.persistence.database import Database
from bolt_core.persistence.models import (
    validate_credential_reference,
    validate_http_url,
    validate_identifier,
    validate_json_object,
    validate_message_content,
    validate_provider_slug,
    validate_workspace_path,
)


class PersistenceConflictError(RuntimeError):
    """A revision no longer matches the durable record."""


_SQLITE_INTEGER_MAX = 2**63 - 1


class ControlPlaneRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save_workspace(self, canonical_path: str | Path) -> str:
        raw_path = validate_workspace_path(canonical_path)
        path = str(Path(raw_path).resolve())
        workspace_id = stable_workspace_identity(path)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into workspaces(workspace_id, canonical_path, created_at, updated_at, revision) "
                "values (?, ?, ?, ?, 0) on conflict(canonical_path) do update set updated_at = excluded.updated_at",
                (workspace_id, path, now, now),
            )
        return workspace_id

    def create_session(self, session_id: str, workspace_id: str, status: str) -> None:
        validate_identifier(session_id)
        validate_identifier(workspace_id)
        validate_identifier(status)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into sessions(id, workspace_id, status, created_at, updated_at) values (?, ?, ?, ?, ?)",
                (session_id, workspace_id, status, now, now),
            )

    def list_sessions(self, workspace_id: str) -> list[str]:
        validate_identifier(workspace_id)
        connection = self.database.connection()
        try:
            return [
                str(row["id"])
                for row in connection.execute(
                    "select id from sessions where workspace_id = ? order by created_at, id",
                    (workspace_id,),
                )
            ]
        finally:
            connection.close()

    def create_task(
        self, task_id: str, workspace_id: str, session_id: str | None, status: str, payload: dict
    ) -> None:
        validate_identifier(task_id)
        validate_identifier(workspace_id)
        if session_id is not None:
            validate_identifier(session_id)
        validate_identifier(status)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into tasks(id, workspace_id, session_id, status, revision, payload_json, created_at, updated_at) "
                "values (?, ?, ?, ?, 0, ?, ?, ?)",
                (task_id, workspace_id, session_id, status, serialized, now, now),
            )

    def create_runtime_session(
        self, runtime_session_id: str, task_id: str, runtime_id: str,
        external_session_id: str, status: str,
    ) -> None:
        validate_identifier(runtime_session_id)
        validate_identifier(task_id)
        validate_identifier(runtime_id)
        validate_identifier(external_session_id)
        validate_identifier(status)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into runtime_sessions(id, task_id, runtime_id, external_session_id, status, created_at, updated_at) "
                "values (?, ?, ?, ?, ?, ?, ?)",
                (runtime_session_id, task_id, runtime_id, external_session_id, status, now, now),
            )

    def append_runtime_event(
        self, event_id: str, runtime_session_id: str, sequence: int, event_type: str, payload: dict
    ) -> None:
        validate_identifier(event_id)
        validate_identifier(runtime_session_id)
        _validate_positive_integer(sequence)
        validate_identifier(event_type)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into runtime_events(id, runtime_session_id, sequence, type, payload_json, created_at) "
                "values (?, ?, ?, ?, ?, ?)",
                (event_id, runtime_session_id, sequence, event_type, serialized, now),
            )

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
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into messages(id, session_id, sequence, role, content, tool_call_id, "
                "metadata_json, created_at) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (message_id, session_id, sequence, role, content, tool_call_id, serialized, now),
            )

    def save_checkpoint(
        self, checkpoint_id: str, task_id: str, task_revision: int, payload: dict,
    ) -> None:
        validate_identifier(checkpoint_id)
        validate_identifier(task_id)
        _validate_nonnegative_integer(task_revision)
        serialized = validate_json_object(payload)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into checkpoints(id, task_id, task_revision, payload_json, created_at) "
                "values (?, ?, ?, ?, ?)",
                (checkpoint_id, task_id, task_revision, serialized, now),
            )

    def save_model_profile(
        self, profile_id: str, workspace_id: str | None, provider: str, base_url: str,
        model: str, temperature: float, timeout: float, context_window: int,
        credential_id: str | None, config: dict,
    ) -> None:
        validate_identifier(profile_id)
        if workspace_id is not None:
            validate_identifier(workspace_id)
        serialized, credential_id = _validate_profile(
            provider, base_url, model, temperature, timeout, context_window, credential_id, config
        )
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "insert into model_profiles(id, workspace_id, provider, base_url, model, temperature, timeout, "
                "context_window, credential_id, revision, config_json, created_at, updated_at) "
                "values (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                (
                    profile_id, workspace_id, provider, base_url, model, temperature, timeout,
                    context_window, credential_id, serialized, now, now,
                ),
            )

    def load_model_profile(self, profile_id: str) -> dict:
        validate_identifier(profile_id)
        connection = self.database.connection()
        try:
            row = connection.execute(
                "select id, workspace_id, provider, base_url, model, temperature, timeout, context_window, "
                "credential_id, revision, config_json from model_profiles where id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(profile_id)
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        return result

    def update_model_profile(self, profile_id: str, expected_revision: int, changes: dict) -> dict:
        validate_identifier(profile_id)
        _validate_nonnegative_integer(expected_revision)
        current = self.load_model_profile(profile_id)
        if current["revision"] != expected_revision:
            raise PersistenceConflictError("model profile revision conflict")
        allowed = {"provider", "base_url", "model", "temperature", "timeout", "context_window", "credential_id", "config"}
        if set(changes) - allowed:
            raise ValueError("unsupported model profile field")
        updated = {**current, **changes}
        serialized, credential_id = _validate_profile(
            updated["provider"], updated["base_url"], updated["model"],
            updated["temperature"], updated["timeout"], updated["context_window"],
            updated["credential_id"], updated["config"],
        )
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "update model_profiles set provider=?, base_url=?, model=?, temperature=?, timeout=?, "
                "context_window=?, credential_id=?, config_json=?, revision=revision+1, updated_at=? "
                "where id=? and revision=? and revision < ?",
                (
                    updated["provider"], updated["base_url"], updated["model"], updated["temperature"],
                    updated["timeout"], updated["context_window"], credential_id, serialized,
                    now, profile_id, expected_revision, _SQLITE_INTEGER_MAX,
                ),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("model profile revision conflict")
        return self.load_model_profile(profile_id)


    def delete_model_profile(self, profile_id: str, expected_revision: int) -> None:
        validate_identifier(profile_id)
        _validate_nonnegative_integer(expected_revision)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "delete from model_profiles where id = ? and revision = ?",
                (profile_id, expected_revision),
            )
        if cursor.rowcount != 1:
            raise PersistenceConflictError("model profile revision conflict")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_profile(
    provider: object, base_url: object, model: object,
    temperature: object, timeout: object, context_window: object,
    credential_id: str | None, config: object,
) -> tuple[str, str | None]:
    validate_provider_slug(provider)
    validate_http_url(base_url)
    validate_identifier(model)
    _validate_finite_number(temperature, minimum=0)
    _validate_finite_number(timeout, minimum=0, exclusive=True)
    _validate_positive_integer(context_window)
    serialized = validate_json_object(config)
    return serialized, validate_credential_reference(credential_id)


def _validate_nonnegative_integer(value: object) -> None:
    if type(value) is not int or not 0 <= value <= _SQLITE_INTEGER_MAX:
        raise ValueError("expected a non-negative SQLite integer")


def _validate_positive_integer(value: object) -> None:
    if type(value) is not int or not 0 < value <= _SQLITE_INTEGER_MAX:
        raise ValueError("expected a positive SQLite integer")


def _validate_finite_number(value: object, *, minimum: int, exclusive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("expected a finite number")
    if value < minimum or (exclusive and value == minimum):
        raise ValueError("numeric value is below the allowed minimum")
