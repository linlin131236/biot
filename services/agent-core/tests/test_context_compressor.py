from bolt_core.conversation import ConversationMessage
from bolt_core.context_compressor import ContextCompressor


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
    roles = [m.role for m in result]
    assert roles[0] == "system"
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
    # Recent window should be preserved
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
    # Should have a summary message for older content
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
