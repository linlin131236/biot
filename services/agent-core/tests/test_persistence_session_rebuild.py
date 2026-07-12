"""Slice A: sessions and messages through the unified ControlPlaneRepository.

Sessions and messages are written transactionally through the repository. After
the Database/Repository object is destroyed, a brand new Repository opened on the
SAME user-data directory must recover the durable records. Sensitive metadata,
sensitive content and secret-bearing values must be rejected.
"""

import sqlite3

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _open_repository(data_root) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(data_root))


def test_messages_persist_in_order_within_a_session(tmp_path):
    repository = _open_repository(tmp_path / "user-data")
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    repository.append_message("m1", "session_123", 1, "user", "hello", None, {})
    repository.append_message("m2", "session_123", 2, "assistant", "hi there", None, {})

    messages = repository.list_messages("session_123")
    assert [m["id"] for m in messages] == ["m1", "m2"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "hello"


def test_sessions_and_messages_survive_repository_rebuild(tmp_path):
    data_root = tmp_path / "user-data"

    # First lifecycle: write, then destroy the Repository + Database objects.
    first = _open_repository(data_root)
    workspace_id = first.save_workspace("C:/Projects/A")
    first.create_session("session_persist", workspace_id, "active")
    first.append_message("m1", "session_persist", 1, "user", "remember me", None, {})
    del first

    # Second lifecycle: brand new objects on the same on-disk user-data.
    second = _open_repository(data_root)
    assert second.list_sessions(workspace_id) == ["session_persist"]
    recovered = second.list_messages("session_persist")
    assert [m["content"] for m in recovered] == ["remember me"]


def test_workspace_identity_is_stable_across_rebuild(tmp_path):
    data_root = tmp_path / "user-data"
    first = _open_repository(data_root)
    first_id = first.save_workspace("C:/Projects/A")
    del first

    second = _open_repository(data_root)
    second_id = second.save_workspace("C:/Projects/A")
    assert second_id == first_id


def test_message_metadata_rejects_secret_without_writing_canary(tmp_path):
    repository = _open_repository(tmp_path / "user-data")
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.append_message(
            "m_secret", "session_123", 1, "user", "hello",
            None, {"apiKey": _SECRET_CANARY},
        )

    assert _SECRET_CANARY not in str(caught.value)
    assert repository.list_messages("session_123") == []


def test_session_for_missing_workspace_is_rejected(tmp_path):
    repository = _open_repository(tmp_path / "user-data")

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_session("session_orphan", "workspace.v1.absent", "active")
