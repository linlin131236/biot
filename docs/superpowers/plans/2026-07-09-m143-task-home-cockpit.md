# M143 Task Home Cockpit Plan

## Goal

Upgrade the liquid glass home screen from a polished composer into a usable Agent cockpit that shows project, permission, run, and core status while offering safe recommended task entry points.

## Scope

- Add a task cockpit section to `LiquidGlassHome`.
- Add six recommended task cards wired to existing safe UI callbacks.
- Disable run-bound cards until a run exists, and keep permission wording aligned with the actual pending-permission action.
- Preserve current composer, command strip, legacy engineering panels, and compatibility text expected by older tests.
- Add focused tests for cockpit state, task card routing, workspace-disabled state, and private-address exclusion.
- Keep all user-visible UI Chinese.

## Non-goals

- No backend execution changes.
- No automatic tool execution or automatic approval.
- No PermissionGate changes.
- No push, release, tag, or delete.

## Acceptance

- New cockpit test fails before implementation and passes after implementation.
- Existing desktop app and dogfood tests stay green.
- Browser check confirms cockpit and six cards render with liquid border flow.
- `pnpm run quality` passes.
- `uv run pytest -q` passes.
- Product UI/source does not contain private address wording.
