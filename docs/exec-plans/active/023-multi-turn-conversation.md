# Exec Plan 023 - Multi-Turn Conversation

## Goal

Turn Bolt from "one goal → N steps → done" into a conversational agent that maintains dialogue history, supports user interruptions, and manages context window.

## Why Now

After Plans 019-022, Bolt can do real work with tools, memory, and sub-agents. But every interaction is a fresh start — no continuity, no way to say "wait, change direction", no context persistence. A real agent needs conversation.

## Scope

### 1. Conversation model

New file: `services/agent-core/src/bolt_core/conversation.py`

```python
@dataclass
class ConversationMessage:
    role: str        # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    timestamp: str = ""

class ConversationStore:
    def __init__(self, db_path: str | None = None):
        # Persist messages in SQLite
    
    def add(self, conversation_id: str, message: ConversationMessage) -> None:
        # Append message
    
    def history(self, conversation_id: str, limit: int = 50) -> list[ConversationMessage]:
        # Get recent messages
    
    def summarize(self, conversation_id: str) -> str:
        # Generate summary of older messages (LLM call)
```

### 2. Update AgentLoop

- Instead of rebuilding context from scratch each step, maintain a `ConversationStore`.
- Each step appends assistant response + tool result to conversation.
- When conversation exceeds token budget, trigger summarization of oldest messages.
- System prompt is always the first message (never summarized away).

### 3. User message injection

- New API endpoint: `POST /conversations/{id}/messages` — user sends a message mid-loop.
- If loop is running, message is queued and injected as a `user` role message at the next step.
- This enables "stop what you're doing, change direction."

### 4. Context compression

New file: `services/agent-core/src/bolt_core/context_compressor.py`

```python
class ContextCompressor:
    def compress(self, messages: list[ConversationMessage], budget: int) -> list[ConversationMessage]:
        # 1. Keep system prompt (always)
        # 2. Keep last N messages (configurable, default 10)
        # 3. Summarize older messages into one "context_summary" user message
        # 4. If still over budget, truncate oldest tool results
        pass
```

When to compress:
- Before each LLM call, check token count (rough estimate: len(text) / 4).
- If over budget (default 128k tokens), compress.

### 5. Conversation persistence

- Conversations stored in SQLite alongside memories.
- New endpoint: `GET /conversations` — list conversations.
- New endpoint: `GET /conversations/{id}` — get conversation history.
- Desktop UI shows conversation history in sidebar.

### 6. Desktop UX

- Chat-style input at bottom of workbench (replace single goal input).
- Messages render as conversation bubbles.
- "New conversation" button.
- Pending permissions still show as cards in the conversation flow.

## Safety Boundary

- Conversation history does NOT change permission rules.
- User interruptions still go through normal tool flow.
- Summarization may lose detail — that's acceptable for context management.
- No conversation data leaves the machine.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_conversation_store_add_and_history`
   - `test_conversation_summarization_triggers_at_budget`
   - `test_user_message_injection_mid_loop`
   - `test_context_compressor_preserves_system_prompt`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `ConversationStore` with SQLite persistence.
- [ ] `ContextCompressor` with token budget enforcement.
- [ ] `AgentLoop` maintains conversation across steps.
- [ ] User can inject messages mid-loop.
- [ ] API endpoints for conversation management.
- [ ] All tests pass.
