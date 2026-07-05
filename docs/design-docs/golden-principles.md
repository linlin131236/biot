# Golden Principles

M11 turns harness engineering rules into checks that Bolt can enforce.

## Boundary Validation

- Workspace paths must pass `PathGuard` before reads, writes, shell workdirs, or generated proposals.
- Secret paths are denied, not summarized or indexed.
- Tools must flow through `ToolRequest`, `PermissionGate`, trace recording, and execution/apply boundaries.

## Structured Traceability

- Tool request, permission decision, execution result, and maintenance proposal events must use stable trace event names.
- Tool failures must record observable result, root cause, repair status, and what not to repeat.
- Self-maintenance actions may propose changes, but writes still require ChangeSet approval.

## Naming

- Trace names use dotted lower-case domains, for example `maintenance.document_gardener.proposed`.
- Memory tags use searchable lower-case tokens such as `failure`, `perception`, and `workspace_profile`.
- Failure pattern files use stable slugs: `{tool}-{operation}-{failure_class}.md`, with repeated terms collapsed.

## Mechanical Enforcement

- `pnpm quality` runs size, docs, boundary, architecture, and package tests.
- CI must run `pnpm quality`, desktop build, and Python pytest.
- Architecture rules live in `scripts/check-architecture.mjs`; docs requirements live in `scripts/check-docs.mjs`.
