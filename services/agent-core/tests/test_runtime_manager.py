from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor, RuntimeSession
from bolt_core.runtime.events import RuntimeEvent, RuntimeEventKind, TaskLifecycle
from bolt_core.runtime.manager import RuntimeManager
from bolt_core.runtime.registry import RuntimeRegistry


@dataclass
class FakeRuntime:
    descriptor: RuntimeDescriptor = field(default_factory=lambda: RuntimeDescriptor(
        runtime_id="bolt-native",
        implementation_version="0.1.0",
        protocol_type="bolt-native",
        protocol_version="v1",
        capabilities=RuntimeCapabilities(messages=True, permissions=True, cancellation=True),
    ))
    calls: list[tuple] = field(default_factory=list)
    fail_cancel: bool = False

    def start(self, task_id, request):
        self.calls.append(("start", task_id, request))
        return RuntimeSession("session_12345678", self.descriptor.runtime_id, task_id)

    def send(self, session, message): self.calls.append(("send", session, message))
    def resume(self, session): self.calls.append(("resume", session))
    def resolve_approval(self, session, approval_id, approved): self.calls.append(("approval", session, approval_id, approved))
    def cancel(self, session):
        self.calls.append(("cancel", session))
        if self.fail_cancel:
            raise RuntimeError("runtime cancel failed")
    def close(self, session): self.calls.append(("close", session))


def _event(kind, sequence, **payload):
    return RuntimeEvent(
        event_id=f"evt_{sequence:08d}", task_id="task_12345678", runtime_id="bolt-native",
        session_id="session_12345678", sequence=sequence, timestamp=datetime.now(UTC),
        kind=kind, payload=payload,
    )


def _manager(on_session_closed=None):
    runtime = FakeRuntime()
    registry = RuntimeRegistry()
    registry.register(runtime.descriptor, runtime)
    return RuntimeManager(registry, on_session_closed=on_session_closed), runtime


def test_manager_starts_only_registered_runtime_and_tracks_session_state():
    manager, runtime = _manager()

    session = manager.start("bolt-native", "task_12345678", {"goal": "read"})

    assert session == RuntimeSession("session_12345678", "bolt-native", "task_12345678")
    assert runtime.calls == [("start", "task_12345678", {"goal": "read"})]
    snapshot = manager.snapshot(session)
    assert snapshot.status == "starting"
    assert snapshot.last_event_sequence == 0
    assert snapshot.implementation_version == "0.1.0"
    assert snapshot.pid is None
    assert snapshot.last_heartbeat is not None
    with pytest.raises(ValueError, match="not registered"):
        manager.start("hermes", "task_12345678", {})


def test_manager_delegates_runtime_lifecycle_only_for_owned_session():
    manager, runtime = _manager()
    session = manager.start("bolt-native", "task_12345678", {})

    manager.send(session, {"text": "hello"})
    manager.resume(session)
    manager.resolve_approval(session, "approval_123", True)
    manager.cancel(session)
    manager.close(session)

    assert [call[0] for call in runtime.calls] == ["start", "send", "resume", "approval", "cancel", "close"]
    with pytest.raises(ValueError, match="unknown runtime session"):
        manager.cancel(RuntimeSession("session_other", "bolt-native", "task_12345678"))


def test_manager_rejects_cross_session_late_and_duplicate_terminal_events():
    manager, _runtime = _manager()
    session = manager.start("bolt-native", "task_12345678", {})
    manager.append_event(session, _event(RuntimeEventKind.STATUS, 1, status="running"))

    with pytest.raises(ValueError, match="session_id"):
        manager.append_event(session, RuntimeEvent(
            event_id="evt_cross_0001", task_id="task_12345678", runtime_id="bolt-native",
            session_id="session_other", sequence=2, timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.MESSAGE_DELTA, payload={"text": "late"},
        ))
    manager.append_event(session, _event(RuntimeEventKind.COMPLETED, 2, summary="done"))
    assert manager.snapshot(session).lifecycle is TaskLifecycle.COMPLETED
    with pytest.raises(ValueError, match="terminal"):
        manager.append_event(session, _event(RuntimeEventKind.COMPLETED, 3, summary="again"))


def test_manager_marks_crashed_session_failed_without_completed_event():
    manager, _runtime = _manager()
    session = manager.start("bolt-native", "task_12345678", {})

    manager.mark_crashed(session)

    snapshot = manager.snapshot(session)
    assert snapshot.lifecycle is TaskLifecycle.FAILED
    assert snapshot.events[-1].kind is RuntimeEventKind.FAILED
    assert snapshot.events[-1].payload["error_code"] == "crashed"


def test_manager_shutdown_closes_sessions_already_revoked_by_terminal_events():
    manager, runtime = _manager()
    session = manager.start("bolt-native", "task_12345678", {})
    manager.append_event(session, _event(RuntimeEventKind.COMPLETED, 1, summary="done"))

    manager.shutdown()

    assert [call[0] for call in runtime.calls] == ["start", "close"]


def test_manager_notifies_once_when_cancel_close_or_terminal_event_ends_session():
    closed = []
    manager, _runtime = _manager(on_session_closed=closed.append)
    session = manager.start("bolt-native", "task_12345678", {})

    manager.cancel(session)
    manager.append_event(session, _event(RuntimeEventKind.CANCELLED, 1, abandoned_tool_ids=[], abandoned_approval_ids=[]))
    manager.close(session)

    assert closed == [session]


def test_manager_notifies_token_revoker_when_runtime_cancel_fails():
    closed = []
    manager, runtime = _manager(on_session_closed=closed.append)
    runtime.fail_cancel = True
    session = manager.start("bolt-native", "task_12345678", {})

    with pytest.raises(RuntimeError, match="cancel failed"):
        manager.cancel(session)

    assert closed == [session]
