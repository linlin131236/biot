# Bolt Agent Map

Bolt is an agent-first desktop AI product. This file is a map, not a manual.

## Start Here

- Architecture: `docs/ARCHITECTURE.md`
- Product scope: `docs/product-specs/bolt-v1.md`
- Active work: `docs/exec-plans/active/`
- Completed decisions: `docs/decisions/`
- Quality rules: `docs/QUALITY_SCORE.md`
- Security rules: `docs/SECURITY.md`
- Harness reference: `docs/references/harness-engineering.md`
- Golden principles: `docs/design-docs/golden-principles.md`
- Failure patterns: `docs/failure-patterns/`

## Engineering Rules

1. Production code must have a failing test first.
2. Run focused tests after each feature.
3. Max 3 fix rounds for the same failing feature; then redesign.
4. Keep functions at or under 30 lines.
5. Keep source files at or under 300 lines.
6. Do not copy-paste implementations.
7. Do not modify unrelated working code.
8. Keep changes surgical and goal-driven.
9. Tool failures must record what failed, why, repair status, and what not to repeat.
10. Writes require a change set and user confirmation before applying.
