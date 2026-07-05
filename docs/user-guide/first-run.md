# First Run Guide

## Agent Core Runtime

Bolt Desktop checks Agent Core on startup and starts the local service automatically when the default URL is down. If startup fails, confirm Python is available or set `BOLT_AGENT_CORE_PYTHON` before launching the desktop app.

## Open Desktop

Run the desktop app in development or install a packaged build. On a fresh profile, Bolt opens the first-run wizard.

## Complete Setup

1. Confirm the workspace path.
2. Confirm the Agent Core URL, usually `http://localhost:8000`.
3. Configure model settings through Agent Core. API keys are not stored in browser localStorage.
4. Enter the workbench.

## Workbench

- `Memory / Perception` shows workspace profile and intent signals.
- `Pending Permissions` shows commands and file diffs that need approval.
- `Harness Trace` shows run and tool events.
- If Bolt cannot reach Agent Core, the sidebar reports `down` and core actions show a visible error banner.

## Recovery

Bolt restores the last workspace, core URL, and last run id from local session state. It does not restore secrets from localStorage.
