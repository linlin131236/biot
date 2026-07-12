"""Slice C: runtime event ordering through the unified ControlPlaneRepository.

Runtime events for one runtime session must have strictly monotonic, gapless
sequence numbers. Duplicate, out-of-order and late events must be rejected. A
cancelled runtime session must not accept further events (no resurrection). A
rejected event must leave no partial row.
"""

import sqlite3

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    RuntimeEventSequenceError,
    RuntimeSessionClosedError,
)


def _repository(tmp_path) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(tmp_path / "user-data"))


def _seed_runtime(repository) -> None:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    repository.create_task("task_123", workspace_id, "session_123", "running", {})
    repository.create_runtime_session(
        "runtime_session_123", "task_123", "bolt-native", "external_123", "running"
    )


def test_events_persist_in_strict_monotonic_order(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)

    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})
    repository.append_runtime_event("event_2", "runtime_session_123", 2, "status", {})
    repository.append_runtime_event("event_3", "runtime_session_123", 3, "status", {})

    events = repository.list_runtime_events("runtime_session_123")
    assert [e["sequence"] for e in events] == [1, 2, 3]


def test_first_event_must_start_at_one(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)

    with pytest.raises(RuntimeEventSequenceError):
        repository.append_runtime_event("event_5", "runtime_session_123", 5, "status", {})


def test_duplicate_sequence_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})

    with pytest.raises((RuntimeEventSequenceError, sqlite3.IntegrityError)):
        repository.append_runtime_event("event_dup", "runtime_session_123", 1, "status", {})


def test_out_of_order_gap_sequence_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})

    with pytest.raises(RuntimeEventSequenceError):
        repository.append_runtime_event("event_gap", "runtime_session_123", 3, "status", {})


def test_late_lower_sequence_is_rejected(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})
    repository.append_runtime_event("event_2", "runtime_session_123", 2, "status", {})

    with pytest.raises(RuntimeEventSequenceError):
        repository.append_runtime_event("event_late", "runtime_session_123", 2, "status", {})


@pytest.mark.parametrize("status", ["cancelled", "completed", "failed"])
def test_closed_runtime_session_rejects_further_events(status, tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})
    repository.close_runtime_session("runtime_session_123", status)

    with pytest.raises(RuntimeSessionClosedError):
        repository.append_runtime_event("event_late", "runtime_session_123", 2, "status", {})

    assert [event["id"] for event in repository.list_runtime_events("runtime_session_123")] == [
        "event_1"
    ]


def test_closed_runtime_session_cannot_be_reopened_for_late_events(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})
    repository.close_runtime_session("runtime_session_123", "cancelled")

    with pytest.raises(RuntimeSessionClosedError):
        repository.set_runtime_session_status("runtime_session_123", "running")
    with pytest.raises(RuntimeSessionClosedError):
        repository.append_runtime_event("event_late", "runtime_session_123", 2, "status", {})

    assert [event["id"] for event in repository.list_runtime_events("runtime_session_123")] == [
        "event_1"
    ]


def test_rejected_event_leaves_no_partial_row(tmp_path):
    repository = _repository(tmp_path)
    _seed_runtime(repository)
    repository.append_runtime_event("event_1", "runtime_session_123", 1, "status", {})

    with pytest.raises(RuntimeEventSequenceError):
        repository.append_runtime_event("event_bad", "runtime_session_123", 9, "status", {})

    events = repository.list_runtime_events("runtime_session_123")
    assert [e["id"] for e in events] == ["event_1"]
