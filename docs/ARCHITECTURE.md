# Architecture

Bolt is split into a desktop shell and a Python Agent Core.

## Layers

1. Desktop Shell: React, Electron, permission UI, trace display, and local workflow UX.
2. Agent Core: harness runs, tool requests, permission queue, permission gates, ToolExecutor, traces, MemoryStore, failure recall, and context packets.
3. Shared Protocol: TypeScript-visible protocol types for desktop and future clients.
4. Quality Harness: tests, size checks, documentation checks, and boundary checks.

## Rule

Tools do not execute directly. They produce requests that flow through permission gates and trace recording before any side effect is allowed.
