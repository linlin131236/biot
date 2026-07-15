"""Registry for pre-approved managed runtime implementations."""

from __future__ import annotations

from bolt_core.runtime.contracts import RuntimeDescriptor, is_runtime_id


class RuntimeRegistry:
    """Resolve only runtime implementations registered by Bolt at startup."""

    def __init__(self) -> None:
        self._runtimes: dict[str, object] = {}
        self._descriptors: dict[str, RuntimeDescriptor] = {}

    def register(self, descriptor: RuntimeDescriptor, runtime: object) -> None:
        if not isinstance(descriptor, RuntimeDescriptor):
            raise ValueError("descriptor must be RuntimeDescriptor")
        if descriptor.runtime_id in self._runtimes:
            raise ValueError("runtime_id is already registered")
        self._runtimes[descriptor.runtime_id] = runtime
        self._descriptors[descriptor.runtime_id] = descriptor

    def resolve(self, runtime_id: str) -> object:
        self._validate_runtime_id(runtime_id)
        try:
            return self._runtimes[runtime_id]
        except KeyError as error:
            raise ValueError("runtime_id is not registered") from error

    def descriptor(self, runtime_id: str) -> RuntimeDescriptor:
        self._validate_runtime_id(runtime_id)
        try:
            return self._descriptors[runtime_id]
        except KeyError as error:
            raise ValueError("runtime_id is not registered") from error

    def descriptors(self) -> tuple[RuntimeDescriptor, ...]:
        return tuple(self._descriptors[runtime_id] for runtime_id in sorted(self._descriptors))

    @staticmethod
    def _validate_runtime_id(runtime_id: object) -> None:
        if not is_runtime_id(runtime_id):
            raise ValueError("runtime_id must be a controlled runtime identifier")
