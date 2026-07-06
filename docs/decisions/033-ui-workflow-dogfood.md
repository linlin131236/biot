# M33 UI Workflow Dogfood + Chinese Desktop Experience

## Status

Accepted.

## Context

M32 proved that the desktop client and backend dogfood paths work. However, the UI still used English for all buttons, panel headings, empty-state text, and sidebar labels. There was also no UI entry for file read/patch operations — the tool flow was only testable via client functions.

## Decision

M33 chinese-ifies all user-visible UI text and adds a ToolFlowPanel with file path input, read file button, old/new text inputs, and submit patch button. All patch operations continue to go through the permission gate (submitToolRequest → pending_permission → approve/reject). No UI bypass is introduced.

The Chinese-first strategy means: all button labels, panel headings, empty-state messages, error messages, and sidebar labels must be in Chinese. Technical proper nouns (Agent Core, Provider, Model, Base URL, Bolt) are retained in English but paired with Chinese labels where they appear as UI text.

Code variable names, API paths, test descriptions, and type definitions remain in English — only user-visible rendered text changes.

## Consequences

The desktop product now presents a Chinese-first experience. Future UI additions must follow the same Chinese-first convention. The uiWorkflowDogfood test suite ensures no English UI text regressions.

M33 does not add new autonomous behavior, release packaging, signing, or online updates.
