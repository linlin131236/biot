# M36 Native Workspace Picker + Electron Security Bridge

## Status

Accepted.

## Context

M35 added workspace binding but used a `prompt()` fallback. Real desktop apps use native OS folder dialogs.

## Decision

- Extract workspace picker logic into `workspacePicker.ts` for testability
- IPC channel: `bolt:select-workspace` (fixed string, not configurable from renderer)
- Preload exposes only `window.bolt.selectWorkspace` via `contextBridge.exposeInMainWorld`
- Renderer does NOT get raw `ipcRenderer`, `fs`, `shell`, or generic `invoke`
- Cancel returns `null`, does not change current workspace
- Non-Electron environments fall back to Chinese prompt

## Consequences

- Renderer cannot invoke arbitrary IPC channels
- Only directory selection is possible (no file read/write through bridge)
- All file operations still go through Agent Core + permission gate + workspace boundary
