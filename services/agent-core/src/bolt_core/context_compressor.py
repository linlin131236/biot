"""Context compressor: manage conversation token budget.

Strategy:
1. Always keep system prompt
2. Always keep messages with permission/safety/failure metadata
3. Keep recent N messages (configurable window)
4. Summarize older messages into one compressed message
"""

from bolt_core.conversation import ConversationMessage


class ContextCompressor:
    def __init__(self, recent_window: int = 10) -> None:
        self._recent_window = recent_window

    def compress(self, messages: list[ConversationMessage],
                 budget: int) -> list[ConversationMessage]:
        if not messages:
            return messages

        # 1. Extract system prompt (always first, always kept)
        system_msg = None
        rest = messages
        if messages[0].role == "system":
            system_msg = messages[0]
            rest = messages[1:]

        # 2. Split into "protected" (permission/failure/evidence) and normal
        protected = []
        normal = []
        for i, msg in enumerate(rest):
            if self._is_protected(msg):
                protected.append((i, msg))
            else:
                normal.append((i, msg))

        # 3. Keep recent window from normal messages
        recent_normal = normal[-self._recent_window:] if len(normal) > self._recent_window else normal
        older_normal = normal[:-self._recent_window] if len(normal) > self._recent_window else []

        # 4. Build summary of older messages
        result = []
        if system_msg:
            result.append(system_msg)

        if older_normal:
            summary_text = self._build_summary(older_normal)
            result.append(ConversationMessage(
                role="user",
                content=summary_text,
                metadata={"compressed": True, "message_count": len(older_normal)},
            ))

        # 5. Merge protected + recent, preserving order
        merged = list(recent_normal) + protected
        merged.sort(key=lambda x: x[0])
        result.extend(msg for _, msg in merged)

        return result

    def _is_protected(self, msg: ConversationMessage) -> bool:
        """Messages with permission, safety, or failure metadata must not be compressed away."""
        safety_keys = {"permission_pending", "step_failed", "permission_denied",
                       "evidence", "safety_boundary"}
        return bool(safety_keys & set(msg.metadata.keys()))

    def _build_summary(self, older: list[tuple[int, ConversationMessage]]) -> str:
        parts = []
        for _, msg in older:
            prefix = msg.role.upper()
            parts.append(f"[{prefix}] {msg.content[:200]}")
        count = len(parts)
        summary = "\n".join(parts)
        return f"[Context summary of {count} earlier messages]\n{summary}"
