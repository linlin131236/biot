# Decision 005 - Read-Only Workspace Tools

## Status

Accepted.

## Context

Bolt needs a safe workspace-reading layer before write tools, shell execution, and LLM-driven agent loops. The read layer must make workspace boundaries explicit and produce traceable tool results.

## Decision

Implement read-only tools in Agent Core:

- `file.read` reads UTF-8 text files inside the configured workspace.
- `files.search` searches file names and text content inside the configured workspace.
- Path safety is enforced through `PathGuard` for reads and candidate search hits.
- The harness auto-executes allowed read-only requests and records permission and execution trace events.
- Desktop and shared TypeScript code use the same `ToolRequest` contract for submitting read-only requests.

## Consequences

M6 can build write tools on top of the existing harness, permission queue, trace log, and tool-result contract without mixing read-only behavior with writes. Read-only tools remain side-effect free and do not bypass workspace or secret-path restrictions.
