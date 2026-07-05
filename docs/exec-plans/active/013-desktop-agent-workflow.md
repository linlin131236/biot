# M13 Desktop Agent Workflow

## Goal

Turn the M12 desktop shell into a usable agent workbench: start runs, execute agent steps, inspect traces, approve permissions, configure models, and trigger memory maintenance.

## Completed Scope

- Goal input and `Start Run` action.
- `Run Step` action with task log updates.
- Trace refresh for the current run.
- Pending permission approve/reject controls with diff and command context.
- Model settings form that sends API keys only to Agent Core.
- Document gardener trigger for the current run.
- Client-side handling for failed Agent Core responses.

## Safety Boundary

- No multi-step autonomous loop.
- No automatic commit, push, publish, or PR creation.
- No browser localStorage API key persistence.
- Permissions still flow through Agent Core approval endpoints.

## Verification

- `services/agent-core/.venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
