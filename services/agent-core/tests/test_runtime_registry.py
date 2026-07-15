import pytest

from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor
from bolt_core.runtime.registry import RuntimeRegistry


def _descriptor(runtime_id: str = "bolt-native") -> RuntimeDescriptor:
    return RuntimeDescriptor(
        runtime_id=runtime_id,
        implementation_version="0.1.0",
        protocol_type="bolt-native",
        protocol_version="v1",
        capabilities=RuntimeCapabilities(messages=True, cancellation=True),
    )


def test_registry_resolves_only_pre_registered_controlled_runtime_ids():
    runtime = object()
    registry = RuntimeRegistry()
    registry.register(_descriptor(), runtime)

    assert registry.resolve("bolt-native") is runtime
    assert registry.descriptor("bolt-native") == _descriptor()
    with pytest.raises(ValueError, match="not registered"):
        registry.resolve("hermes")


@pytest.mark.parametrize("runtime_id", ["../hermes", "C:/hermes", "hermes.exe", "bad id"])
def test_registry_rejects_uncontrolled_runtime_identifiers(runtime_id):
    registry = RuntimeRegistry()

    with pytest.raises(ValueError, match="runtime_id"):
        registry.resolve(runtime_id)


def test_registry_rejects_duplicate_runtime_registration():
    registry = RuntimeRegistry()
    registry.register(_descriptor(), object())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_descriptor(), object())
