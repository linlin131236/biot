# Bolt

Bolt is a desktop AI Agent built for local, permission-aware work. The first milestone is a safe coding assistant with explicit file diffs, command confirmation, and failure memory.

## Workspace

```text
apps/desktop          Electron + React desktop shell
services/agent-core   Python Agent Core
packages/shared       Shared protocol definitions
docs                  Architecture notes and decisions
tests/e2e             End-to-end tests
```

## Development

```bash
pnpm install
pnpm test
cd services/agent-core && python -m pytest
```
