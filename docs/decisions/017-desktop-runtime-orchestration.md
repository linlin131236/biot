# 017 Desktop Runtime Orchestration

## Context

M16 made workspace selection a real runtime contract, but the desktop app still assumed Agent Core was already running at a URL. That made Bolt feel like a web client attached to a manually managed backend instead of a desktop agent.

## Decision

M17 moves Agent Core lifecycle ownership into the Electron main process:

- Electron checks the Agent Core health endpoint when the app starts.
- If the endpoint is down, Electron starts `uvicorn bolt_core.app:create_app --factory` on `127.0.0.1`.
- Runtime paths are resolved from the repo checkout in development and from Electron resources in packaged builds.
- `BOLT_AGENT_CORE_PORT`, `BOLT_AGENT_CORE_PYTHON`, `BOLT_AGENT_CORE_ROOT`, and `BOLT_AGENT_CORE_SRC` can override the default runtime.
- The renderer checks `/health` when the workbench opens and reflects `ok` or `down` in the sidebar.
- Packaged builds include the Agent Core source tree as an Electron resource, but do not include a Python virtual environment.

## Consequences

Developers and early users no longer need to start the Python service manually for the default local path. The runtime remains conservative: it binds only to localhost, does not publish network services, and stops the child process when the desktop app exits.

Future hardening can bundle a managed Python runtime or build Agent Core into a standalone binary. Until then, packaged builds require a compatible Python environment or explicit runtime overrides.
