# M34 Chinese Desktop Quality

## Status

Accepted.

## Context

M33 added Chinese UI text and tool flow, but no quality gate existed to prevent mojibake or tool-protocol regressions from entering the repo. The tool protocol also needed canonical names (`file.read` / `file.patch` with `old_string` / `new_string`) rather than bare `"file"` with `old_text` / `new_text`.

## Decision

Add `scripts/check-chinese-ui.mjs` as a quality gate that:
1. Detects mojibake characters (UTF-8 misread as GBK patterns)
2. Enforces canonical tool protocol (`file.read`/`file.patch`, `old_string`/`new_string`)
3. Is wired into `pnpm quality` as `lint:chinese-ui`

Also fixed test mock data from `tool: "file"` to `tool: "file.patch"` for consistency.

## Consequences

Future commits with mojibake or bare tool names will be caught by `pnpm lint:chinese-ui` before merge. The gate does not check code variable names or API paths — only user-visible text and tool protocol payloads.
