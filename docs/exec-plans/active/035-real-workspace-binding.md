# M35 Real Workspace File Picker + Safe Workspace Binding

## Goal

Let the Bolt desktop bind to a real workspace directory, persist it, support relative file paths, and reject all path traversal/escape attacks. All file ops must be safe-guarded by workspace boundary.

## Scope

- Workspace picker UI (choose/change workspace, persist to session)
- Relative path resolution (README.md, src/app.ts)
- Path traversal denial (../outside.txt)
- Sibling prefix traversal denial (project vs project_evil)
- Secret path denial (.env)
- file.patch still requires pending_permission
- M35 does NOT add Agent intelligence, release, or auto-update

## Changes

### Backend (services/agent-core)

- `risk.py:_is_inside_workspace`: replaced startswith with relative_to (fixes sibling prefix)
- `path_guard.py:check`: resolve relative paths against workspace first (`ws / target`)
- `harness.py:_queue_file_patch`: use PathGuard instead of raw _is_inside_workspace

### Desktop (apps/desktop)

- `App.tsx`: added selectWorkspace adapter, changeWorkspace action, "更换工作区/选择工作区" button, "工作区未选择" display, hasWorkspace guard on toolbar buttons, relative path placeholder
- `uiWorkflowDogfood.test.tsx`: added M35 workspace binding tests (4 new)

### Tests

- `test_workspace_binding.py`: 9 new pytest tests (relative path, traversal, sibling prefix, secret)
- `uiWorkflowDogfood.test.tsx`: 4 new vitest tests (workspace button, empty workspace, relative path, disabled actions)

## Verification

- 299 pytest (including 9 workspace binding)
- 15 vitest desktop (including 4 M35 workspace)
- pnpm quality (lint:size, lint:docs, lint:boundaries, lint:architecture, lint:chinese-ui)
- desktop build
