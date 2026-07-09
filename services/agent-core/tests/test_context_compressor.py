from bolt_core.conversation import ConversationMessage
from bolt_core.context_compressor import ContextCompressor, _TOOL_CONTENT_LIMIT, _TOKEN_ESTIMATE_RATIO


# ── helpers ───────────────────────────────────────────────────────────────────

def _tokens(msg: ConversationMessage) -> int:
    return max(1, len(msg.content) // _TOKEN_ESTIMATE_RATIO)


def _total_tokens(msgs: list[ConversationMessage]) -> int:
    return sum(_tokens(m) for m in msgs)


# ── original behaviour tests ──────────────────────────────────────────────────

def test_compressor_preserves_system_prompt():
    compressor = ContextCompressor(recent_window=2)
    messages = [
        ConversationMessage(role="system", content="You are Bolt."),
        ConversationMessage(role="user", content="Old msg 1"),
        ConversationMessage(role="user", content="Old msg 2"),
        ConversationMessage(role="user", content="Old msg 3"),
        ConversationMessage(role="assistant", content="Recent reply"),
        ConversationMessage(role="user", content="Recent msg"),
    ]

    result = compressor.compress(messages, budget=10000)
    assert result[0].role == "system"
    assert result[0].content == "You are Bolt."


def test_compressor_keeps_recent_window():
    compressor = ContextCompressor(recent_window=2)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="user", content="Old 1"),
        ConversationMessage(role="user", content="Old 2"),
        ConversationMessage(role="user", content="Old 3"),
        ConversationMessage(role="assistant", content="Recent reply"),
        ConversationMessage(role="user", content="Recent msg"),
    ]

    result = compressor.compress(messages, budget=10000)
    contents = [m.content for m in result]
    assert "Recent reply" in contents
    assert "Recent msg" in contents


def test_compressor_summarizes_older_messages():
    compressor = ContextCompressor(recent_window=2)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="user", content="Very old message 1"),
        ConversationMessage(role="user", content="Very old message 2"),
        ConversationMessage(role="user", content="Very old message 3"),
        ConversationMessage(role="assistant", content="Recent"),
        ConversationMessage(role="user", content="Latest"),
    ]

    result = compressor.compress(messages, budget=10000)
    summary_msgs = [m for m in result if m.metadata.get("compressed")]
    assert len(summary_msgs) == 1


def test_compressor_preserves_permission_evidence():
    compressor = ContextCompressor(recent_window=1)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="assistant", content="Need approval",
                           metadata={"permission_pending": True}),
        ConversationMessage(role="user", content="Latest"),
    ]

    result = compressor.compress(messages, budget=10000)
    perm_msgs = [m for m in result if m.metadata.get("permission_pending")]
    assert len(perm_msgs) == 1


def test_compressor_preserves_failure_evidence():
    compressor = ContextCompressor(recent_window=1)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="assistant", content="Step failed",
                           metadata={"step_failed": True}),
        ConversationMessage(role="user", content="Latest"),
    ]

    result = compressor.compress(messages, budget=10000)
    fail_msgs = [m for m in result if m.metadata.get("step_failed")]
    assert len(fail_msgs) == 1


# ── P1 regression: budget constrains final output ─────────────────────────────

def test_compressor_output_fits_budget():
    """Estimated token count of all output messages must not exceed budget."""
    compressor = ContextCompressor(recent_window=3)
    # 7 messages of 80 chars → 20 tokens each; system 40 chars → 10 tokens
    msg_content = "Y" * 80
    messages = [
        ConversationMessage(role="system", content="S" * 40),
    ] + [
        ConversationMessage(role="user", content=msg_content) for _ in range(7)
    ]
    budget = 150
    result = compressor.compress(messages, budget=budget)

    total = _total_tokens(result)
    assert total <= budget, f"output ({total} tokens) exceeds budget ({budget})"


def test_compressor_budget_limits_window():
    """When budget is tight, fewer recent messages are kept than recent_window allows."""
    compressor = ContextCompressor(recent_window=10)  # cap = 10; budget is binding
    msg_content = "X" * 100  # 25 tokens each
    messages = [
        ConversationMessage(role="system", content="S" * 40),   # 10 tokens
        ConversationMessage(role="user", content=msg_content),
        ConversationMessage(role="user", content=msg_content),
        ConversationMessage(role="user", content=msg_content),
        ConversationMessage(role="user", content=msg_content),
        ConversationMessage(role="user", content="NEWEST_" + msg_content),
    ]
    # system(10) + 3×25=75 = 85 ≤ 100; adding a 4th would reach 110 > 90 remaining
    budget = 100
    result = compressor.compress(messages, budget=budget)

    total = _total_tokens(result)
    assert total <= budget, f"output ({total} tokens) exceeds budget ({budget})"

    contents = [m.content for m in result]
    assert any("NEWEST_" in c for c in contents), "newest message must be kept"

    # recent_window=10 would allow all 5; budget must limit it to fewer
    full_msgs = [m for m in result
                 if m.role != "system" and not m.metadata.get("compressed")]
    assert len(full_msgs) < 5, "budget must limit window below recent_window cap"


def test_compressor_budget_zero_excludes_all_normal():
    """Budget too tight for normal messages: all go to summary (or dropped)."""
    compressor = ContextCompressor(recent_window=10)
    messages = [
        ConversationMessage(role="system", content="S" * 10000),
        ConversationMessage(role="user", content="msg1"),
        ConversationMessage(role="user", content="msg2"),
    ]
    # budget = exactly system tokens → nothing left for normal
    system_tokens = _tokens(messages[0])
    result = compressor.compress(messages, budget=system_tokens)

    full_normal = [m for m in result
                   if m.role != "system" and not m.metadata.get("compressed")]
    assert full_normal == [], "no full normal messages should survive at zero budget"

    total = _total_tokens(result)
    assert total <= system_tokens + 5, (
        f"output ({total} tokens) should not exceed system budget ({system_tokens})"
    )


def test_compressor_summary_fits_budget_with_many_older():
    """When there are many older messages the summary is trimmed, not unbounded."""
    compressor = ContextCompressor(recent_window=2)
    # 50 older messages + 2 recent; tight budget
    old_msgs = [ConversationMessage(role="user", content="old " * 10) for _ in range(50)]
    recent_msgs = [
        ConversationMessage(role="assistant", content="recent A"),
        ConversationMessage(role="user", content="recent B"),
    ]
    messages = [ConversationMessage(role="system", content="Sys")] + old_msgs + recent_msgs
    budget = 200
    result = compressor.compress(messages, budget=budget)

    total = _total_tokens(result)
    assert total <= budget, (
        f"output ({total} tokens) must not exceed budget ({budget}) "
        f"even with 50 older messages"
    )
    # Both recents must survive
    contents = [m.content for m in result]
    assert "recent A" in contents
    assert "recent B" in contents


# ── P1 regression: tool message content is truncated ─────────────────────────

def test_compressor_truncates_tool_content():
    """Tool messages over _TOOL_CONTENT_LIMIT chars must be truncated."""
    compressor = ContextCompressor(recent_window=10)
    big_content = "T" * (_TOOL_CONTENT_LIMIT + 500)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="tool", content=big_content, tool_call_id="call_1"),
    ]

    result = compressor.compress(messages, budget=100000)
    tool_msgs = [m for m in result if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert len(tool_msgs[0].content) < len(big_content), "tool content must be truncated"
    assert len(tool_msgs[0].content) <= _TOOL_CONTENT_LIMIT + 60, "within limit + notice"
    assert tool_msgs[0].metadata.get("tool_content_truncated") is True


def test_compressor_short_tool_content_not_truncated():
    """Tool messages under _TOOL_CONTENT_LIMIT must not be modified."""
    compressor = ContextCompressor(recent_window=10)
    short_content = "ok result"
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="tool", content=short_content, tool_call_id="call_1"),
    ]

    result = compressor.compress(messages, budget=100000)
    tool_msgs = [m for m in result if m.role == "tool"]
    assert tool_msgs[0].content == short_content
    assert not tool_msgs[0].metadata.get("tool_content_truncated")


# ── defensive: metadata=None must not crash ───────────────────────────────────

def test_compressor_handles_none_metadata():
    """metadata=None on plain messages must not raise AttributeError."""
    compressor = ContextCompressor(recent_window=5)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="user", content="hello", metadata=None),
        ConversationMessage(role="assistant", content="world", metadata=None),
    ]
    # Should not raise
    result = compressor.compress(messages, budget=10000)
    assert len(result) >= 2


def test_compressor_tool_with_none_metadata_does_not_raise():
    """Oversized tool message with metadata=None must not raise TypeError
    inside _truncate_tool_content when spreading the metadata dict."""
    compressor = ContextCompressor(recent_window=10)
    big_content = "T" * (_TOOL_CONTENT_LIMIT + 1)
    messages = [
        ConversationMessage(role="system", content="System"),
        ConversationMessage(role="tool", content=big_content,
                            tool_call_id="call_x", metadata=None),
    ]
    # Previously raised: TypeError: 'NoneType' object is not a mapping
    result = compressor.compress(messages, budget=100000)
    tool_msgs = [m for m in result if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].metadata.get("tool_content_truncated") is True
