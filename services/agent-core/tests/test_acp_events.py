import pytest

from bolt_core.runtime.acp_events import map_acp_update, prompt_usage_payload
from bolt_core.runtime.events import RuntimeEventKind


def test_acp_maps_agent_message_thought_and_plan_updates():
    message = map_acp_update({
        "sessionUpdate": "agent_message_chunk",
        "content": {"type": "text", "text": "hello"},
    })
    thought = map_acp_update({
        "sessionUpdate": "agent_thought_chunk",
        "content": {"type": "text", "text": "considering"},
    })
    plan = map_acp_update({
        "sessionUpdate": "plan",
        "entries": [{"content": "inspect", "status": "in_progress"}],
    })

    assert message == (RuntimeEventKind.MESSAGE_DELTA, {"text": "hello"})
    assert thought == (RuntimeEventKind.THOUGHT, {"text": "considering"})
    assert plan == (RuntimeEventKind.PLAN_UPDATE, {"entries": [{"content": "inspect", "status": "in_progress"}]})


def test_acp_maps_tool_lifecycle_with_stable_tool_identity():
    started = map_acp_update({
        "sessionUpdate": "tool_call",
        "toolCallId": "tool_123",
        "title": "Read README",
        "kind": "read",
        "rawInput": {"path": "README.md"},
    })
    completed = map_acp_update({
        "sessionUpdate": "tool_call_update",
        "toolCallId": "tool_123",
        "title": "Read README",
        "status": "completed",
        "rawOutput": "content",
    })

    assert started == (
        RuntimeEventKind.TOOL_STARTED,
        {"tool_id": "tool_123", "title": "Read README", "tool_kind": "read"},
    )
    assert completed == (
        RuntimeEventKind.TOOL_COMPLETED,
        {"tool_id": "tool_123", "title": "Read README"},
    )


def test_acp_distinguishes_context_update_and_prompt_token_usage():
    context = map_acp_update({"sessionUpdate": "usage_update", "size": 128000, "used": 2345})
    prompt = prompt_usage_payload({
        "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30, "thoughtTokens": 4},
    })

    assert context == (RuntimeEventKind.USAGE_UPDATE, {"context_window": 128000, "context_used": 2345})
    assert prompt == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30, "thought_tokens": 4}


@pytest.mark.parametrize(
    "update",
    [
        {"sessionUpdate": "tool_call", "toolCallId": "bad id", "title": "bad"},
        {"sessionUpdate": "tool_call_update", "toolCallId": "tool_123", "title": "bad", "status": "unexpected"},
        {"sessionUpdate": "usage_update", "size": 10, "used": -1},
        {"sessionUpdate": "agent_message_chunk", "content": {"type": "image"}},
    ],
)
def test_acp_rejects_unknown_or_malformed_update_fail_closed(update):
    with pytest.raises(ValueError, match="ACP"):
        map_acp_update(update)
