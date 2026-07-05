# Exec Plan 020 - Core Tool Expansion

## Goal

Expand Bolt's tool set from 3 read-only tools to the minimum viable set for real coding work. After this plan, Bolt can read, search, write, edit, and run commands in a workspace.

## Why Now

Plan 019 makes the LLM actually drive tools via function calling. But with only file.read / files.search / shell.execute, the agent cannot modify anything. A coding agent that can only read is not useful.

## Current Tool Inventory

| Tool | Operation | Status |
|---|---|---|
| file.read | read | ✅ Working |
| files.search | search | ✅ Working |
| shell.execute | command | ✅ Working (read-only via PermissionGate) |
| file.write | write | ⚠️ Framework exists (ChangeSet + confirm) but agent loop never auto-uses it |

## New Tools to Add

### 1. `file.patch` — Surgical Edit

The most important missing tool. Without it, every edit requires rewriting the entire file.

Schema:
```json
{
  "name": "file.patch",
  "description": "Apply a targeted find-and-replace edit to a file. Prefer this over file.write for small changes.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "File path in workspace"},
      "old_string": {"type": "string", "description": "Exact text to find (must be unique in file)"},
      "new_string": {"type": "string", "description": "Replacement text"}
    },
    "required": ["path", "old_string", "new_string"]
  }
}
```

Implementation in `patch_engine.py` (already exists as 60 lines!):
- Read file → find `old_string` → verify unique → replace → write back.
- If `old_string` not found or not unique → return error with context.
- Goes through PermissionGate as `confirm_with_diff` (show the diff before applying).

### 2. `file.write` — Full File Write (upgrade existing)

Currently has ChangeSet flow but the agent loop doesn't drive it properly. Fix:
- After Plan 019's conversation loop, file.write tool calls flow naturally: LLM calls file.write → PermissionGate shows diff → user approves → write executes.
- No new code needed in the tool itself, just make sure the agent loop wiring passes it through.

### 3. `terminal.spawn` — Background Process

For long-running commands (dev servers, watchers, test suites).

Schema:
```json
{
  "name": "terminal.spawn",
  "description": "Start a long-running command in the background. Returns a session_id.",
  "parameters": {
    "type": "object",
    "properties": {
      "command": {"type": "string"},
      "workdir": {"type": "string"},
      "notify_on_complete": {"type": "boolean", "default": true}
    },
    "required": ["command"]
  }
}
```

New file: `services/agent-core/src/bolt_core/background_executor.py`
- Uses `subprocess.Popen` to spawn.
- Stores process in a dict keyed by session_id.
- PermissionGate: `confirm` level (same as shell.execute).
- Returns session_id + initial output.
- New endpoint: `POST /terminal/{session_id}/poll` to check status.
- New endpoint: `POST /terminal/{session_id}/kill` to stop.

### 4. `web.search` — Web Search

For looking up documentation, error messages, solutions.

Schema:
```json
{
  "name": "web.search",
  "description": "Search the web for information. Returns titles, URLs, and descriptions.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "limit": {"type": "integer", "default": 5, "description": "Max results"}
    },
    "required": ["query"]
  }
}
```

New file: `services/agent-core/src/bolt_core/web_tools.py`
- Uses `urllib.request` to call a configurable search API (SearXNG, Brave, Google Custom Search).
- Default: SearXNG local instance or public API.
- PermissionGate: `allow` level (read-only, no side effects).
- Returns list of {title, url, description}.

### 5. `web.extract` — Web Page Content

Schema:
```json
{
  "name": "web.extract",
  "description": "Extract text content from web page URLs. Returns markdown.",
  "parameters": {
    "type": "object",
    "properties": {
      "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to extract (max 5)"},
      "char_limit": {"type": "integer", "default": 15000}
    },
    "required": ["urls"]
  }
}
```

In same `web_tools.py`:
- Fetches URL, strips HTML to markdown via `html.parser` (stdlib, no new deps).
- PermissionGate: `allow` level.

## Permission Gate Updates

File: `services/agent-core/src/bolt_core/permission_gate.py`

Update `SUPPORTED_OPERATIONS`:
```python
SUPPORTED_OPERATIONS = {
    "file.read": {"read"},
    "files.search": {"search"},
    "file.write": {"write"},
    "file.patch": {"patch"},
    "shell.execute": {"command"},
    "terminal.spawn": {"spawn"},
    "terminal.poll": {"poll"},
    "terminal.kill": {"kill"},
    "web.search": {"search"},
    "web.extract": {"extract"},
}
```

Risk classifications:
- `file.patch` → `confirm_with_diff` (show diff before applying)
- `terminal.spawn` → `confirm` (running commands needs approval)
- `terminal.poll`, `terminal.kill` → `confirm` (interacting with running processes)
- `web.search`, `web.extract` → `allow` (read-only, no workspace side effects)

## Risk Updates

File: `services/agent-core/src/bolt_core/risk.py`

- Add `classify_web_request()` → always `allow`.
- Add `classify_patch(path, workspace)` → `confirm_with_diff` if inside workspace, `deny` if outside.
- Add `classify_background_command(command)` → same rules as `classify_command` but elevated risk for long-running processes.

## Shared Protocol Updates

File: `packages/shared/src/protocol.ts`

Add TypeScript types for new tool payloads, results, and background process state.

## Tool Schema Updates

File: `services/agent-core/src/bolt_core/tool_schemas.py` (created in Plan 019)

Add schemas for all new tools listed above.

## API Endpoint Updates

File: `services/agent-core/src/bolt_core/app.py`

New endpoints:
- `GET /terminal` — list running background processes
- `POST /terminal/{session_id}/poll` — check process output
- `POST /terminal/{session_id}/kill` — kill process
- `GET /terminal/{session_id}/output` — full output

## Safety Boundary

- All write operations (file.write, file.patch) still require ChangeSet + user confirmation.
- All shell commands (shell.execute, terminal.spawn) still require user confirmation.
- Web tools are read-only, no data exfiltration possible.
- Background processes are tracked and killable.
- No new network egress except to configured search API endpoint.
- File operations remain workspace-scoped (PathGuard enforced).

## Verification

1. `services/agent-core/.venv/Scripts/python -I -m pytest` — all tests pass.
2. `pnpm quality` — size, docs, boundary checks pass.
3. New tool tests:
   - `test_patch_applies_unique_replacement`
   - `test_patch_rejects_non_unique_old_string`
   - `test_patch_rejects_missing_old_string`
   - `test_background_executor_spawn_and_poll`
   - `test_background_executor_kill`
   - `test_web_search_returns_results` (mock HTTP)
   - `test_web_extract_returns_markdown` (mock HTTP)
4. Source files under 300 lines each.
5. Manual smoke test: create a run, ask "Read README.md, then add a comment at the top saying 'Bolt was here'". Verify file.patch flows through PermissionGate with diff.

## Acceptance Criteria

- [ ] `file.patch` tool implemented with unique-match validation and diff preview.
- [ ] `file.write` properly wired through agent loop conversation.
- [ ] `terminal.spawn/poll/kill` background process management.
- [ ] `web.search` and `web.extract` with configurable API endpoint.
- [ ] PermissionGate and risk updated for all new tools.
- [ ] Shared protocol types updated.
- [ ] Tool schemas updated for function calling.
- [ ] All tests pass. Source files under 300 lines.
- [ ] Smoke test documented in `docs/references/m20-smoke-test.md`.
