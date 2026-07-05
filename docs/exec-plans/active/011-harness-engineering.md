# M11 Harness Engineering

## Goal

Make Bolt maintain its own codebase through mechanical checks, failure pattern docs, and permissioned maintenance proposals.

## Completed Scope

- Keep `AGENTS.md` as a short repository map.
- Add golden principles as checked repository documentation.
- Add an architecture linter to reject cross-layer imports and direct side-effect boundaries.
- Add a document gardener that proposes failure pattern docs through `file.write` and ChangeSet review.
- Add CI wiring for quality, desktop build, and Python tests.

## Safety Boundary

- No background writer.
- No automatic git commit, push, or PR creation.
- Maintenance writes must use `ToolRequest -> PermissionGate -> ChangeSet -> approval`.
- Failure docs are generated only from local MemoryStore failure records.

## Verification

- `cd services/agent-core && pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `node scripts/check-architecture.mjs`
