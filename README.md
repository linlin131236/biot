# Bolt

Bolt is a desktop AI Agent built for local, permission-aware work. It reads workspace context, proposes file diffs, asks before commands or writes, and records failures for future runs.

## Workspace

```text
apps/desktop          Electron + React desktop shell
services/agent-core   Python Agent Core
packages/shared       Shared protocol definitions
docs                  Architecture notes, decisions, and user guides
```

## Development

```bash
pnpm install
pnpm quality
pnpm --filter @bolt/desktop build
cd services/agent-core
.venv/Scripts/python -I -m pytest
```

## First Run

1. Start Agent Core from `services/agent-core`.
2. Open the desktop app.
3. Confirm the workspace path and Agent Core URL in the first-run wizard.
4. Configure model settings through Agent Core.
5. Use pending permission panels to review command approvals and file diffs.

Bolt stores only non-sensitive desktop session state in localStorage: wizard completion, workspace path, core URL, and last run id. API keys are not stored there.

## Packaging

```bash
pnpm --filter @bolt/desktop package:win
```

The Windows packaging path is configured for local installer/portable artifacts. Code signing, auto-update, and release publishing are future work.

## User Guide

See `docs/user-guide/first-run.md` for setup, workbench, permissions, and recovery behavior.
