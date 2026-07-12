"""Coordinates conversation persistence onto the single source of truth.

When a ControlPlaneRepository is configured, conversations and messages are
persisted exclusively through it (sessions/messages tables). The legacy
ConversationStore is only used when no repository is configured (non-production
/ in-memory tests). No dual-write, no fallback, no adapter shim.
"""

from __future__ import annotations

from uuid import uuid4

from bolt_core.desktop_runner import stable_workspace_identity


class ConversationCoordinator:
    def __init__(self, workspace: str, persistence=None, legacy_store=None) -> None:
        self._workspace = workspace
        self._persistence = persistence
        self._legacy = legacy_store
        self._workspace_id: str | None = None

    @property
    def uses_repository(self) -> bool:
        return self._persistence is not None

    def _ensure_workspace(self) -> str:
        if self._workspace_id is None:
            self._workspace_id = self._persistence.save_workspace(self._workspace)
        return self._workspace_id

    def _ensure_session(self, conversation_id: str) -> None:
        workspace_id = self._ensure_workspace()
        existing = self._persistence.list_sessions(workspace_id)
        if conversation_id not in existing:
            self._persistence.create_session(conversation_id, workspace_id, "active")

    def create(self, conversation_id: str | None, system_prompt: str) -> str:
        cid = conversation_id or f"conv_{uuid4().hex[:8]}"
        if not self.uses_repository:
            if system_prompt:
                self._legacy_add(cid, "system", system_prompt, {})
            return cid
        self._ensure_session(cid)
        if system_prompt:
            self.add_message(cid, "system", system_prompt, {})
        return cid

    def add_message(self, conversation_id: str, role: str, content: str, metadata: dict) -> None:
        if not self.uses_repository:
            self._legacy_add(conversation_id, role, content, metadata)
            return
        self._ensure_session(conversation_id)
        sequence = len(self._persistence.list_messages(conversation_id)) + 1
        self._persistence.append_message(
            f"msg_{uuid4().hex[:12]}", conversation_id, sequence, role, content, None, metadata or {},
        )

    def history(self, conversation_id: str) -> list[dict]:
        if not self.uses_repository:
            return [m.to_dict() for m in self._legacy.history(conversation_id)]
        return [
            {
                "role": record["role"],
                "content": record["content"],
                "tool_call_id": record["tool_call_id"],
                "tool_calls": None,
                "timestamp": record["created_at"],
                "metadata": record["metadata"],
            }
            for record in self._persistence.list_messages(conversation_id)
        ]

    def list_conversations(self) -> list[str]:
        if not self.uses_repository:
            return self._legacy.list_conversations()
        return self._persistence.list_sessions(self._ensure_workspace())

    def _legacy_add(self, conversation_id: str, role: str, content: str, metadata: dict) -> None:
        from bolt_core.conversation import ConversationMessage

        self._legacy.add(
            conversation_id, ConversationMessage(role=role, content=content, metadata=metadata or {}),
        )
