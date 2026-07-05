# M18 Packaged Runtime Smoke

## Status

Accepted.

## Context

M17 made the desktop shell start Agent Core automatically in development and packaged modes. A packaged Windows artifact can still fail if Electron Builder omits `agent-core` resources or if the runtime path points at a layout that only exists in the repo workspace.

## Decision

Packaged mode resolves Agent Core from Electron's `resources/agent-core` directory. Before spawning Python, the supervisor fails closed when the packaged `bolt_core/app.py` or `pyproject.toml` resource is missing.

Windows `dir` packaging runs a runtime smoke check after Electron Builder completes. The smoke check verifies:

- Electron Builder includes `services/agent-core/src` as `agent-core/src`.
- Electron Builder includes `services/agent-core/pyproject.toml` as `agent-core/pyproject.toml`.
- `apps/desktop/release/win-unpacked/resources/agent-core/src/bolt_core/app.py` exists after `package:win:dir`.
- `apps/desktop/release/win-unpacked/resources/agent-core/pyproject.toml` exists after `package:win:dir`.

The default quality gate runs the same script without requiring package output, so normal CI can validate configuration without creating Windows artifacts.

## Consequences

Packaged runtime failures now point at missing release resources instead of timing out as a generic health failure. M18 still does not bundle Python, publish releases, sign artifacts by default, or enable auto-update.
