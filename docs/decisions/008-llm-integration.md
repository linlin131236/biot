# Decision 008 - LLM Integration

## Status

Accepted.

## Context

Bolt needs model-driven planning after read, write, and shell tools have been placed behind permission and trace boundaries. Model calls introduce two new risks: tool bypass and accidental secret exposure through configuration or network requests.

## Decision

Introduce a model gateway and one-step agent loop:

- Default execution uses a deterministic fake model gateway for local tests.
- OpenAI-compatible model calls share the same gateway interface and require explicit runtime settings.
- Model settings keep API keys in process memory and expose only redacted status.
- The agent loop accepts only strict JSON tool requests from model output.
- Every model-produced tool request is submitted through `Harness.submit_tool_request`.
- Trace events record context building, planner/model/verifier activity, token usage, and agent step completion.

## Consequences

M8 gives Bolt a real agent-loop boundary without weakening M5-M7 safety. Future work can add persistent encrypted key storage, richer planning, streaming model responses, and Desktop settings UI without changing the core permission contract.
