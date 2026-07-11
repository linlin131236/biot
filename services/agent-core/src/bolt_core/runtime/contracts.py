"""Runtime-neutral contracts for Bolt's managed agent control plane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol

_RUNTIME_NAME = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_PROTOCOL_VERSION = re.compile(r"^v[1-9][0-9]*$")
_STABLE_ID = re.compile(r"^[a-z][a-z0-9_-]{2,127}$")
_CAPABILITIES = frozenset({
    "messages", "planning", "tools", "file_changes", "shell", "permissions",
    "cancellation", "resumption", "mcp", "images",
})


def is_runtime_id(value: object) -> bool:
    """Return whether *value* uses Bolt's canonical runtime identifier grammar."""
    return isinstance(value, str) and _RUNTIME_NAME.fullmatch(value) is not None


class RuntimeErrorCode(str, Enum):
    UNAVAILABLE = "unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    PROTOCOL_FAILED = "protocol_failed"
    TIMEOUT = "timeout"
    CRASHED = "crashed"
    CANCELLED = "cancelled"
    RESUME_FAILED = "resume_failed"


@dataclass(frozen=True)
class RuntimeCapabilities:
    messages: bool = False
    planning: bool = False
    tools: bool = False
    file_changes: bool = False
    shell: bool = False
    permissions: bool = False
    cancellation: bool = False
    resumption: bool = False
    mcp: bool = False
    images: bool = False

    def __post_init__(self) -> None:
        for capability in _CAPABILITIES:
            if not isinstance(getattr(self, capability), bool):
                raise ValueError(f"runtime capability {capability} must be boolean")

    def supports(self, capability: str) -> bool:
        if capability not in _CAPABILITIES:
            raise ValueError(f"unknown runtime capability: {capability}")
        return getattr(self, capability)


@dataclass(frozen=True)
class RuntimeDescriptor:
    runtime_id: str
    implementation_version: str
    protocol_type: str
    protocol_version: str
    capabilities: RuntimeCapabilities

    def __post_init__(self) -> None:
        if not is_runtime_id(self.runtime_id):
            raise ValueError("runtime_id must be a stable lowercase identifier")
        if (
            not isinstance(self.implementation_version, str)
            or not self.implementation_version.strip()
            or any(char.isspace() for char in self.implementation_version)
        ):
            raise ValueError("implementation_version is required and cannot contain whitespace")
        if not is_runtime_id(self.protocol_type):
            raise ValueError("protocol_type must be a stable lowercase identifier")
        if (
            not isinstance(self.protocol_version, str)
            or not _PROTOCOL_VERSION.fullmatch(self.protocol_version)
        ):
            raise ValueError("protocol_version must use v<positive-integer>")
        if not isinstance(self.capabilities, RuntimeCapabilities):
            raise ValueError("capabilities must be RuntimeCapabilities")


@dataclass(frozen=True)
class RuntimeSession:
    session_id: str
    runtime_id: str
    task_id: str

    def __post_init__(self) -> None:
        for name in ("session_id", "task_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _STABLE_ID.fullmatch(value):
                raise ValueError(f"{name} must be a stable identifier")
        if not is_runtime_id(self.runtime_id):
            raise ValueError("runtime_id must be a stable lowercase identifier")


class AgentRuntime(Protocol):
    @property
    def descriptor(self) -> RuntimeDescriptor: ...

    def start(self, task_id: str, request: dict) -> RuntimeSession: ...

    def send(self, session: RuntimeSession, message: dict) -> None: ...

    def resume(self, session: RuntimeSession) -> None: ...

    def resolve_approval(self, session: RuntimeSession, approval_id: str, approved: bool) -> None: ...

    def cancel(self, session: RuntimeSession) -> None: ...

    def close(self, session: RuntimeSession) -> None: ...
