# Decision 013: Desktop Agent Workflow

## Status

Accepted.

## Context

After M12, Bolt can launch into a first-run desktop shell, but the core agent workflow still needs to be driven from the UI. Agent Core already exposes runs, agent steps, traces, permissions, model settings, memory, and document gardening.

## Decision

M13 wires the existing Agent Core capabilities into the desktop without adding new privileged execution paths. The desktop can create runs, run one agent step, refresh trace/memory/permissions, approve or reject pending requests, save model settings, and trigger the document gardener.

## Consequences

- Bolt becomes usable as an interactive agent workbench.
- Side effects remain controlled by Agent Core permission endpoints.
- API keys are sent only to Agent Core and are not persisted in localStorage.
- Multi-step autonomy and replanning remain future work.
