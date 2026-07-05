# Exec Plan 005 - Read-Only Workspace Tools

## Goal

Complete Milestone 5 so Bolt can safely read and search workspace files.

## Completed Scope

- Added `file.read` support for UTF-8 text files inside the workspace.
- Added `files.search` support for name, content, and combined search modes.
- Search excludes `node_modules`, `.git`, `dist`, `.venv`, and Python cache directories.
- Read and search requests flow through the harness and record trace events.
- Workspace-external paths and secret paths are denied before read execution.
- Shared TypeScript protocol now includes `ToolRequest`.
- Desktop harness client can submit tool requests to Agent Core.

## Safety Boundary

Read-only tools cannot write files, run commands, delete files, or access the network. `file.read` is guarded by `PathGuard`; `files.search` only walks the configured workspace and skips excluded directories and secret paths.

## Verification

- Python pytest passes.
- pnpm quality passes.
- desktop build passes.
