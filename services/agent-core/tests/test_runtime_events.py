from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest

from bolt_core.runtime.events import (
    RuntimeEvent,
    RuntimeEventKind,
    RuntimeEventStream,
    TaskLifecycle,
)


def _event(kind: RuntimeEventKind, sequence: int, **payload) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"evt_{sequence:08d}",
        task_id="task_12345678",
        runtime_id="bolt-native",
        session_id="session_12345678",
        sequence=sequence,
        timestamp=datetime(2026, 7, 11, tzinfo=UTC),
        kind=kind,
        payload=payload,
    )


def test_runtime_event_round_trips_required_envelope_fields():
    event = _event(RuntimeEventKind.MESSAGE_DELTA, 1, text="hello")

    restored = RuntimeEvent.from_dict(event.to_dict())

    assert restored == event
    assert restored.to_dict()["timestamp"] == "2026-07-11T00:00:00+00:00"


def test_runtime_event_payload_is_deeply_immutable_and_serialization_is_detached():
    source = {"text": "safe", "nested": {"items": ["original"]}}
    event = _event(RuntimeEventKind.MESSAGE_DELTA, 1, **source)

    source["text"] = "tampered"
    source["nested"]["items"].append("tampered")
    serialized = event.to_dict()
    serialized["payload"]["nested"]["items"].append("serialized-tamper")

    assert event.payload["text"] == "safe"
    assert event.payload["nested"]["items"] == ("original",)
    with pytest.raises(TypeError):
        event.payload["text"] = "forbidden"


@pytest.mark.parametrize("sequence", [True, 1.5, "1"])
def test_runtime_event_rejects_non_integer_sequence_at_constructor_boundary(sequence):
    with pytest.raises(ValueError, match="positive integer"):
        RuntimeEvent(
            event_id="evt_00000001", task_id="task_12345678", runtime_id="bolt-native",
            session_id="session_12345678", sequence=sequence, timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.MESSAGE_DELTA, payload={"text": "hello"},
        )


@pytest.mark.parametrize("sequence", [True, 1.5, "1"])
def test_runtime_event_rejects_non_integer_sequence_at_deserialization_boundary(sequence):
    payload = _event(RuntimeEventKind.MESSAGE_DELTA, 1, text="hello").to_dict()
    payload["sequence"] = sequence

    with pytest.raises(ValueError, match="positive integer"):
        RuntimeEvent.from_dict(payload)


@pytest.mark.parametrize("payload", [None, [], "payload"])
def test_runtime_event_rejects_non_object_payload_at_constructor_boundary(payload):
    with pytest.raises(ValueError, match="payload"):
        RuntimeEvent(
            event_id="evt_00000001", task_id="task_12345678", runtime_id="bolt-native",
            session_id="session_12345678", sequence=1, timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.MESSAGE_DELTA, payload=payload,
        )


@pytest.mark.parametrize("payload", [None, [], "payload"])
def test_runtime_event_rejects_non_object_payload_at_deserialization_boundary(payload):
    event = _event(RuntimeEventKind.MESSAGE_DELTA, 1, text="hello").to_dict()
    event["payload"] = payload

    with pytest.raises(ValueError, match="payload"):
        RuntimeEvent.from_dict(event)


def test_runtime_event_rejects_unknown_kind_at_direct_constructor_boundary():
    with pytest.raises(ValueError, match="unsupported runtime event"):
        RuntimeEvent(
            event_id="evt_00000001", task_id="task_12345678", runtime_id="bolt-native",
            session_id="session_12345678", sequence=1, timestamp=datetime.now(UTC),
            kind="permission.bypassed", payload={},
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", None),
        ("task_id", 123),
        ("runtime_id", []),
        ("session_id", object()),
        ("timestamp", "2026-07-11T00:00:00+00:00"),
    ],
)
def test_runtime_event_rejects_wrong_envelope_types_with_value_error(field, value):
    values = {
        "event_id": "evt_00000001",
        "task_id": "task_12345678",
        "runtime_id": "bolt-native",
        "session_id": "session_12345678",
        "sequence": 1,
        "timestamp": datetime.now(UTC),
        "kind": RuntimeEventKind.MESSAGE_DELTA,
        "payload": {"text": "hello"},
    }
    values[field] = value

    with pytest.raises(ValueError):
        RuntimeEvent(**values)


def test_runtime_event_from_dict_rejects_non_object_envelope_with_value_error():
    with pytest.raises(ValueError, match="envelope"):
        RuntimeEvent.from_dict([])


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (RuntimeEventKind.APPROVAL_REQUESTED, {}),
        (RuntimeEventKind.TOOL_STARTED, {}),
        (RuntimeEventKind.FILE_CHANGE, {}),
        (RuntimeEventKind.TOOL_PROGRESS, {}),
        (RuntimeEventKind.TOOL_COMPLETED, {}),
        (RuntimeEventKind.TOOL_FAILED, {}),
        (RuntimeEventKind.APPROVAL_RESOLVED, {}),
    ],
)
def test_security_sensitive_events_require_explicit_payload(kind, payload):
    with pytest.raises(ValueError, match="payload"):
        _event(kind, 1, **payload)


@pytest.mark.parametrize(
    ("kind", "payload", "field"),
    [
        (RuntimeEventKind.TOOL_STARTED, {"tool_id": 123}, "tool_id"),
        (RuntimeEventKind.TOOL_PROGRESS, {"tool_id": "bad id"}, "tool_id"),
        (
            RuntimeEventKind.APPROVAL_REQUESTED,
            {"approval_id": ["approval_123"]},
            "approval_id",
        ),
        (
            RuntimeEventKind.APPROVAL_RESOLVED,
            {"approval_id": "bad id", "approved": True},
            "approval_id",
        ),
    ],
)
def test_security_sensitive_ids_require_stable_strings(kind, payload, field):
    with pytest.raises(ValueError, match=field):
        _event(kind, 1, **payload)


@pytest.mark.parametrize("status", ["", "completed", "magic"])
def test_runtime_status_event_rejects_unknown_or_terminal_state(status):
    with pytest.raises(ValueError, match="status"):
        _event(RuntimeEventKind.STATUS, 1, status=status)


def test_runtime_status_event_rejects_missing_status_with_stable_contract_error():
    with pytest.raises(ValueError, match="payload requires status"):
        _event(RuntimeEventKind.STATUS, 1)


@pytest.mark.parametrize("error_code", ["", "not_a_runtime_error"])
def test_failed_event_requires_known_runtime_error_code(error_code):
    with pytest.raises(ValueError, match="error_code"):
        _event(RuntimeEventKind.FAILED, 1, error_code=error_code)


def test_approval_resolution_requires_boolean_decision():
    with pytest.raises(ValueError, match="approved"):
        _event(RuntimeEventKind.APPROVAL_RESOLVED, 1, approval_id="approval_123", approved="yes")


def test_event_stream_rejects_duplicate_or_non_monotonic_sequence():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.STATUS, 1, status="running"))

    with pytest.raises(ValueError, match="sequence"):
        stream.append(_event(RuntimeEventKind.MESSAGE_DELTA, 1, text="duplicate"))
    with pytest.raises(ValueError, match="sequence"):
        stream.append(_event(RuntimeEventKind.MESSAGE_DELTA, 0, text="late"))
    with pytest.raises(ValueError, match="expected 2"):
        stream.append(_event(RuntimeEventKind.MESSAGE_DELTA, 3, text="gap"))


def test_event_stream_accepts_only_one_competing_first_event():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    workers = 16
    barrier = Barrier(workers)

    def append_competing_event(index: int) -> bool:
        event = RuntimeEvent(
            event_id=f"evt_competing_{index:08d}",
            task_id="task_12345678",
            runtime_id="bolt-native",
            session_id="session_12345678",
            sequence=1,
            timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.MESSAGE_DELTA,
            payload={"text": str(index)},
        )
        barrier.wait()
        try:
            stream.append(event)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=workers) as executor:
        accepted = list(executor.map(append_competing_event, range(workers)))

    assert sum(accepted) == 1
    assert len(stream.events()) == 1


def test_event_stream_rejects_duplicate_event_id():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.STATUS, 1, status="running"))
    duplicate = RuntimeEvent(
        event_id="evt_00000001", task_id="task_12345678", runtime_id="bolt-native",
        session_id="session_12345678", sequence=2, timestamp=datetime.now(UTC),
        kind=RuntimeEventKind.MESSAGE_DELTA, payload={"text": "duplicate id"},
    )

    with pytest.raises(ValueError, match="event_id"):
        stream.append(duplicate)


def test_event_stream_rejects_events_from_another_runtime_session_or_task():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")

    with pytest.raises(ValueError, match="runtime_id"):
        stream.append(RuntimeEvent(
            event_id="evt_00000001", task_id="task_12345678", runtime_id="other-runtime",
            session_id="session_12345678", sequence=1, timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.STATUS, payload={"status": "running"},
        ))


def test_event_stream_rejects_tool_progress_before_tool_start():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")

    with pytest.raises(ValueError, match="active tool"):
        stream.append(_event(RuntimeEventKind.TOOL_PROGRESS, 1, tool_id="tool_123"))


def test_event_stream_rejects_approval_resolution_without_request():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")

    with pytest.raises(ValueError, match="pending approval"):
        stream.append(_event(RuntimeEventKind.APPROVAL_RESOLVED, 1, approval_id="approval_123", approved=True))


def test_event_stream_rejects_duplicate_tool_start():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.TOOL_STARTED, 1, tool_id="tool_123"))

    with pytest.raises(ValueError, match="already active"):
        stream.append(_event(RuntimeEventKind.TOOL_STARTED, 2, tool_id="tool_123"))


@pytest.mark.parametrize(
    ("first", "payload"),
    [
        (RuntimeEventKind.APPROVAL_REQUESTED, {"approval_id": "approval_123"}),
        (RuntimeEventKind.TOOL_STARTED, {"tool_id": "tool_123"}),
    ],
)
def test_terminal_event_rejects_unresolved_tool_or_approval(first, payload):
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(first, 1, **payload))

    with pytest.raises(ValueError, match="unresolved"):
        stream.append(_event(RuntimeEventKind.COMPLETED, 2, summary="done"))


def test_terminal_event_is_final_and_later_regular_events_cannot_revive_task():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.COMPLETED, 1, summary="done"))

    with pytest.raises(ValueError, match="terminal"):
        stream.append(_event(RuntimeEventKind.STATUS, 2, status="running"))
    assert stream.lifecycle is TaskLifecycle.COMPLETED


def test_terminal_lifecycle_is_read_only_and_cannot_be_revived_by_assignment():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.COMPLETED, 1, summary="done"))

    with pytest.raises(AttributeError):
        stream.lifecycle = TaskLifecycle.RUNNING
    with pytest.raises(ValueError, match="terminal"):
        stream.append(_event(RuntimeEventKind.STATUS, 2, status="running"))


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (RuntimeEventKind.COMPLETED, {"summary": "again"}),
        (
            RuntimeEventKind.FAILED,
            {
                "error_code": "crashed",
                "abandoned_tool_ids": [],
                "abandoned_approval_ids": [],
            },
        ),
        (
            RuntimeEventKind.CANCELLED,
            {"abandoned_tool_ids": [], "abandoned_approval_ids": []},
        ),
    ],
)
def test_terminal_event_rejects_every_later_terminal_event(kind, payload):
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.COMPLETED, 1, summary="done"))

    with pytest.raises(ValueError, match="terminal"):
        stream.append(_event(kind, 2, **payload))


@pytest.mark.parametrize(
    ("terminal_kind", "terminal_payload", "expected_lifecycle"),
    [
        (
            RuntimeEventKind.CANCELLED,
            {
                "abandoned_tool_ids": ["tool_123"],
                "abandoned_approval_ids": ["approval_123"],
            },
            TaskLifecycle.CANCELLED,
        ),
        (
            RuntimeEventKind.FAILED,
            {
                "error_code": "crashed",
                "abandoned_tool_ids": ["tool_123"],
                "abandoned_approval_ids": ["approval_123"],
            },
            TaskLifecycle.FAILED,
        ),
    ],
)
def test_cancel_or_failure_can_abandon_in_flight_work(
    terminal_kind, terminal_payload, expected_lifecycle
):
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.TOOL_STARTED, 1, tool_id="tool_123"))
    stream.append(
        _event(RuntimeEventKind.APPROVAL_REQUESTED, 2, approval_id="approval_123")
    )

    stream.append(_event(terminal_kind, 3, **terminal_payload))

    assert stream.lifecycle is expected_lifecycle
    assert stream.in_flight() == {"tool_ids": [], "approval_ids": []}


def test_terminal_abandonment_must_exactly_match_in_flight_work():
    stream = RuntimeEventStream("task_12345678", "bolt-native", "session_12345678")
    stream.append(_event(RuntimeEventKind.TOOL_STARTED, 1, tool_id="tool_123"))

    with pytest.raises(ValueError, match="abandoned_tool_ids"):
        stream.append(
            _event(
                RuntimeEventKind.CANCELLED,
                2,
                abandoned_tool_ids=["other_tool"],
                abandoned_approval_ids=[],
            )
        )

    assert stream.lifecycle is TaskLifecycle.RUNNING
    assert stream.in_flight() == {"tool_ids": ["tool_123"], "approval_ids": []}


def test_runtime_event_runtime_id_uses_descriptor_identifier_grammar():
    with pytest.raises(ValueError, match="runtime_id"):
        RuntimeEvent(
            event_id="evt_00000001",
            task_id="task_12345678",
            runtime_id="bolt_native",
            session_id="session_12345678",
            sequence=1,
            timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.MESSAGE_DELTA,
            payload={"text": "hello"},
        )


@pytest.mark.parametrize("unknown", ["unknown", "permission.bypassed", ""])
def test_unknown_event_kind_is_explicitly_unsupported(unknown):
    with pytest.raises(ValueError, match="unsupported runtime event"):
        RuntimeEvent.from_dict({
            "event_id": "evt_00000001", "task_id": "task_12345678", "runtime_id": "bolt-native",
            "session_id": "session_12345678", "sequence": 1,
            "timestamp": "2026-07-11T00:00:00+00:00", "kind": unknown, "payload": {},
        })
