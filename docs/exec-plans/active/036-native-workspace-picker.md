# M36 Native Workspace Picker + Electron Security Bridge

## Goal

Replace the frontend fallback prompt with a real Electron native folder dialog and a secure preload bridge.

## Scope

- Electron main process IPC handler for `bolt:select-workspace`
- Preload bridge exposing only `window.bolt.selectWorkspace`
- Renderer `defaultSelectWorkspace` uses `window.bolt` first, fallback prompt for non-Electron
- BrowserWindow security config locked (contextIsolation: true, nodeIntegration: false)

## Out of Scope

- No new Agent intelligence capabilities
- No release / package
- No M37
- No auto-update
- No MoA / subagent / skills execution

## Files Changed

- `electron/workspacePicker.ts` — extracted handler + IPC registration
- `electron/preload.ts` — contextBridge exposing only `bolt.selectWorkspace`
- `electron/main.ts` — register IPC on app ready
- `src/App.tsx` — defaultSelectWorkspace uses `window.bolt`
- `src/global.d.ts` — Window.bolt type declaration
