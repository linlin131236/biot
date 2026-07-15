import pytest

from bolt_core.runtime.native_runtime import BoltNativeRuntime


def test_native_runtime_implements_controlled_runtime_contract():
    runtime = BoltNativeRuntime()

    session = runtime.start("task_12345678", {"goal": "summarize"})
    runtime.send(session, {"text": "continue"})
    runtime.resume(session)
    runtime.resolve_approval(session, "approval_123", False)
    runtime.cancel(session)
    runtime.close(session)

    assert session.runtime_id == "bolt-native"
    assert runtime.descriptor.capabilities.supports("cancellation") is True


def test_native_runtime_rejects_session_from_another_runtime():
    runtime = BoltNativeRuntime()
    session = runtime.start("task_12345678", {})

    with pytest.raises(ValueError, match="runtime_id"):
        runtime.cancel(type(session)(session.session_id, "hermes", session.task_id))
