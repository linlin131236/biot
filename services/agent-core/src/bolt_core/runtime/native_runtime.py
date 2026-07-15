"""In-process adapter for Bolt's existing native runtime contract."""

from __future__ import annotations

from uuid import uuid4

from bolt_core.runtime.contracts import (
    RuntimeCapabilities,
    RuntimeDescriptor,
    RuntimeSession,
)


class BoltNativeRuntime:
    """Expose native Bolt lifecycle without granting new execution capabilities."""

    def __init__(self) -> None:
        self._sessions: set[str] = set()
        self._descriptor = RuntimeDescriptor(
            runtime_id="bolt-native",
            implementation_version="0.1.0",
            protocol_type="bolt-native",
            protocol_version="v1",
            capabilities=RuntimeCapabilities(
                messages=True,
                planning=True,
                tools=True,
                permissions=True,
                cancellation=True,
                resumption=True,
            ),
        )

    @property
    def descriptor(self) -> RuntimeDescriptor:
        return self._descriptor

    def start(self, task_id: str, request: dict) -> RuntimeSession:
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        session = RuntimeSession(f"session_{uuid4().hex}", self._descriptor.runtime_id, task_id)
        self._sessions.add(session.session_id)
        return session

    def send(self, session: RuntimeSession, message: dict) -> None:
        if not isinstance(message, dict):
            raise ValueError("message must be an object")
        self._require_session(session)

    def resume(self, session: RuntimeSession) -> None:
        self._require_session(session)

    def resolve_approval(self, session: RuntimeSession, approval_id: str, approved: bool) -> None:
        if not isinstance(approval_id, str) or not approval_id:
            raise ValueError("approval_id is required")
        if not isinstance(approved, bool):
            raise ValueError("approved must be boolean")
        self._require_session(session)

    def cancel(self, session: RuntimeSession) -> None:
        self._require_session(session)

    def close(self, session: RuntimeSession) -> None:
        self._require_session(session)
        self._sessions.remove(session.session_id)

    def _require_session(self, session: RuntimeSession) -> None:
        if not isinstance(session, RuntimeSession):
            raise ValueError("session must be RuntimeSession")
        if session.runtime_id != self._descriptor.runtime_id:
            raise ValueError("session runtime_id does not match native runtime")
        if session.session_id not in self._sessions:
            raise ValueError("unknown native runtime session")
