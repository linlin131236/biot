# M34 Chinese Desktop Quality

## Goal

Ensure Chinese UI text in the Bolt desktop is real UTF-8 Chinese (not mojibake) and stays that way via a quality gate. Fix tool protocol to use canonical `file.read` / `file.patch` + `old_string` / `new_string`.

## Scope

- Add `scripts/check-chinese-ui.mjs` mojibake + tool-protocol quality gate
- Wire `lint:chinese-ui` into `pnpm quality`
- Fix any remaining `tool: "file"` or `old_text`/`new_text` in test mocks
- M34 docs

## Out of Scope

- New agent intelligence, planner, or model integration (M35+)
- Release packaging or auto-update
- Changing code variable names or API paths to Chinese

## Mojibake Detection Strategy

The gate scans for known mojibake characters and the Unicode replacement character. The detected Unicode codepoints are listed in the script as U+9352, U+93C3, U+7481, U+922B, U+5BF0, U+6FEE, U+93B5, U+7039, and U+FFFD. It also checks that tool protocol uses `file.read` / `file.patch` (not bare `"file"`) and `old_string` / `new_string` (not `old_text` / `new_text`).

## Verification

- `pnpm lint:chinese-ui` passes (exit 0)
- `rg` for mojibake Unicode patterns in `apps/desktop/src docs/` returns zero hits
- `rg "tool: 'file'|old_text|new_text" apps/desktop/src/` returns zero hits
- pytest + pnpm quality + desktop build all green
