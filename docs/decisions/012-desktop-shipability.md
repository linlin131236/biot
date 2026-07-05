# Decision 012: Desktop Shipability

## Status

Accepted.

## Context

Bolt has a permissioned Agent Core, memory, perception, and self-maintenance guardrails. The desktop shell still needs first-run setup, understandable state, recovery, packaging, and user-facing docs.

## Decision

M12 makes the desktop UI state-driven and ship-oriented without weakening the harness. The app persists only non-sensitive session state in localStorage, displays memory/perception and pending permission diffs, and adds Windows packaging configuration.

## Consequences

- Fresh installs start in a guided first-run flow.
- Last workspace, core URL, and last run id can be restored after restart.
- API keys remain outside browser localStorage.
- Installer packaging is configured, while signing and auto-update remain future work.
