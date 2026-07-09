"""Context compressor: manage conversation token budget.

Strategy:
1. Always keep system prompt
2. Always keep messages with permission/safety/failure metadata
3. Keep recent N messages (configurable window), bounded by token budget
4. Summarise older messages into one compressed message (budget-bounded)
5. Truncate oversized tool result content before compression
"""

from bolt_core.conversation import ConversationMessage

# Characters per token approximation (conservative; real tokenisers vary).
_TOKEN_ESTIMATE_RATIO = 4
# Maximum characters kept in a tool result before truncation.
_TOOL_CONTENT_LIMIT = 2000
# Maximum number of older messages included in the summary.
_MAX_SUMMARY_ENTRIES = 20
# Estimated chars for the summary header line.
_SUMMARY_HEADER_CHARS = 50


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

        # 2. Truncate oversized tool content before any window calculation
        rest = [self._truncate_tool_content(msg) for msg in rest]

        # 3. Split into "protected" (permission/failure/evidence) and normal
        protected: list[tuple[int, ConversationMessage]] = []
        normal: list[tuple[int, ConversationMessage]] = []
        for i, msg in enumerate(rest):
            if self._is_protected(msg):
                protected.append((i, msg))
            else:
                normal.append((i, msg))

        # 4. Budget accounting: tokens already committed to system + protected
        committed = (self._estimate_tokens(system_msg) if system_msg else 0)
        committed += sum(self._estimate_tokens(msg) for _, msg in protected)
        remaining = max(0, budget - committed)

        # 5. Recent window: fill from newest, stop when budget exhausted
        window = self._fit_window(normal, remaining)
        if 0 < window < len(normal):
            recent_normal = normal[-window:]
            older_normal = normal[:-window]
        elif window <= 0:
            recent_normal = []
            older_normal = normal
        else:
            recent_normal = normal
            older_normal = []

        # 6. Summary: use whatever budget is left after recent messages
        result: list[ConversationMessage] = []
        if system_msg:
            result.append(system_msg)

        if older_normal:
            recent_cost = sum(self._estimate_tokens(m) for _, m in recent_normal)
            summary_budget = max(0, remaining - recent_cost)
            visible_older = self._select_summary_messages(older_normal, summary_budget)
            if visible_older:
                summary_text = self._build_summary(visible_older)
                dropped = len(older_normal) - len(visible_older)
                result.append(ConversationMessage(
                    role="user",
                    content=summary_text,
                    metadata={
                        "compressed": True,
                        "message_count": len(older_normal),
                        **({"dropped_count": dropped} if dropped else {}),
                    },
                ))

        # 7. Merge protected + recent, preserving original order
        merged = list(recent_normal) + protected
        merged.sort(key=lambda x: x[0])
        result.extend(msg for _, msg in merged)

        return result

    # ── private helpers ───────────────────────────────────────────────────────

    def _fit_window(self, normal: list[tuple[int, ConversationMessage]],
                    token_budget: int) -> int:
        """Return window size: most-recent messages fitting within token_budget,
        capped at self._recent_window."""
        if token_budget <= 0:
            return 0
        total = 0
        count = 0
        for _, msg in reversed(normal):
            cost = self._estimate_tokens(msg)
            if total + cost > token_budget:
                break
            total += cost
            count += 1
            if count >= self._recent_window:
                break
        return count

    def _select_summary_messages(
        self,
        older: list[tuple[int, ConversationMessage]],
        summary_budget: int,
    ) -> list[tuple[int, ConversationMessage]]:
        """Select the most-recent older messages that fit within summary_budget.

        Iterates from newest-of-older to oldest, accumulating cost from the
        actual content length (capped at 200 chars per line) until the budget
        is exhausted or _MAX_SUMMARY_ENTRIES is reached.
        """
        if not older or summary_budget <= 0:
            return []
        overhead = max(1, _SUMMARY_HEADER_CHARS // _TOKEN_ESTIMATE_RATIO)
        if summary_budget <= overhead:
            return []
        avail = summary_budget - overhead
        selected: list[tuple[int, ConversationMessage]] = []
        used = 0
        for idx, msg in reversed(older):
            # "[ROLE] " prefix (≈7 chars) + content[:200] + newline
            line_chars = 8 + min(len(str(msg.content)), 200)
            line_cost = max(1, line_chars // _TOKEN_ESTIMATE_RATIO)
            if used + line_cost > avail:
                break
            used += line_cost
            selected.append((idx, msg))
            if len(selected) >= _MAX_SUMMARY_ENTRIES:
                break
        return list(reversed(selected))

    def _estimate_tokens(self, msg: ConversationMessage) -> int:
        """Rough token estimate: characters / ratio."""
        return max(1, len(msg.content) // _TOKEN_ESTIMATE_RATIO)

    def _truncate_tool_content(self, msg: ConversationMessage) -> ConversationMessage:
        """Truncate oversized tool result messages to _TOOL_CONTENT_LIMIT chars."""
        if msg.role == "tool" and len(msg.content) > _TOOL_CONTENT_LIMIT:
            dropped = len(msg.content) - _TOOL_CONTENT_LIMIT
            truncated = (
                msg.content[:_TOOL_CONTENT_LIMIT]
                + f"\n[…{dropped} chars truncated]"
            )
            return ConversationMessage(
                role=msg.role,
                content=truncated,
                tool_call_id=msg.tool_call_id,
                tool_calls=msg.tool_calls,
                timestamp=msg.timestamp,
                metadata={**(msg.metadata or {}), "tool_content_truncated": True},
            )
        return msg

    def _is_protected(self, msg: ConversationMessage) -> bool:
        """Messages with permission, safety, or failure metadata must not be compressed away."""
        safety_keys = {"permission_pending", "step_failed", "permission_denied",
                       "evidence", "safety_boundary"}
        return bool(safety_keys & set((msg.metadata or {}).keys()))

    def _build_summary(self, older: list[tuple[int, ConversationMessage]]) -> str:
        parts = []
        for _, msg in older:
            prefix = msg.role.upper()
            parts.append(f"[{prefix}] {str(msg.content)[:200]}")
        count = len(parts)
        summary = "\n".join(parts)
        return f"[Context summary of {count} earlier messages]\n{summary}"
