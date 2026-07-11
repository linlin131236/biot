import pytest

from bolt_core.runtime.contracts import (
    AgentRuntime,
    RuntimeCapabilities,
    RuntimeDescriptor,
    RuntimeErrorCode,
    RuntimeSession,
)


def test_runtime_descriptor_requires_known_protocol_and_version():
    descriptor = RuntimeDescriptor(
        runtime_id="bolt-native",
        implementation_version="0.1.0",
        protocol_type="bolt-native",
        protocol_version="v1",
        capabilities=RuntimeCapabilities(messages=True, planning=True, tools=True),
    )

    assert descriptor.runtime_id == "bolt-native"
    assert descriptor.capabilities.supports("messages") is True
    assert descriptor.capabilities.supports("mcp") is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"runtime_id": "bad id"}, "runtime_id"),
        ({"implementation_version": ""}, "implementation_version"),
        ({"protocol_type": ""}, "protocol_type"),
        ({"protocol_version": "version 1"}, "protocol_version"),
        ({"capabilities": object()}, "capabilities"),
    ],
)
def test_runtime_descriptor_rejects_invalid_identity(kwargs, message):
    values = {
        "runtime_id": "bolt-native",
        "implementation_version": "0.1.0",
        "protocol_type": "bolt-native",
        "protocol_version": "v1",
        "capabilities": RuntimeCapabilities(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        RuntimeDescriptor(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_id", None),
        ("implementation_version", None),
        ("protocol_type", 1),
        ("protocol_version", []),
    ],
)
def test_runtime_descriptor_rejects_wrong_identity_types_with_value_error(field, value):
    values = {
        "runtime_id": "bolt-native",
        "implementation_version": "0.1.0",
        "protocol_type": "bolt-native",
        "protocol_version": "v1",
        "capabilities": RuntimeCapabilities(),
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        RuntimeDescriptor(**values)


def test_runtime_capabilities_reject_non_boolean_values():
    with pytest.raises(ValueError, match="boolean"):
        RuntimeCapabilities(messages="yes")


def test_runtime_session_binds_stable_runtime_task_and_session_ids():
    session = RuntimeSession(
        session_id="session_12345678",
        runtime_id="bolt-native",
        task_id="task_12345678",
    )

    assert session.runtime_id == "bolt-native"
    with pytest.raises(ValueError, match="session_id"):
        RuntimeSession("invalid id", "bolt-native", "task_12345678")


@pytest.mark.parametrize(
    "values",
    [
        (None, "bolt-native", "task_12345678"),
        ("session_12345678", None, "task_12345678"),
        ("session_12345678", "bolt-native", 123),
    ],
)
def test_runtime_session_rejects_wrong_identity_types_with_value_error(values):
    with pytest.raises(ValueError, match="stable"):
        RuntimeSession(*values)


def test_runtime_capabilities_fail_closed_for_unknown_capability():
    capabilities = RuntimeCapabilities(shell=True, images=True)

    assert capabilities.supports("shell") is True
    with pytest.raises(ValueError, match="unknown runtime capability"):
        capabilities.supports("teleport")


def test_runtime_error_codes_are_stable_and_exhaustive():
    assert RuntimeErrorCode.UNAVAILABLE.value == "unavailable"
    assert RuntimeErrorCode.AUTHENTICATION_FAILED.value == "authentication_failed"
    assert RuntimeErrorCode.PROTOCOL_FAILED.value == "protocol_failed"
    assert RuntimeErrorCode.TIMEOUT.value == "timeout"
    assert RuntimeErrorCode.CRASHED.value == "crashed"
    assert RuntimeErrorCode.CANCELLED.value == "cancelled"
    assert RuntimeErrorCode.RESUME_FAILED.value == "resume_failed"


def test_agent_runtime_protocol_declares_lifecycle_methods():
    required = {"descriptor", "start", "send", "resume", "resolve_approval", "cancel", "close"}

    assert required <= set(AgentRuntime.__dict__)
