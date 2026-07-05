# Exec Plan 001 - Harness Foundation

## Goal

Build the first harness engineering layer for Bolt: protocol, permission gate, trace, failure constraints, documentation checks, and desktop visibility.

## Steps

1. Make repository knowledge agent-readable.
2. Add documentation and boundary quality gates.
3. Add Python tool protocol models.
4. Add permission gate around risk classification.
5. Add trace event recording.
6. Add harness run state machine.
7. Expose harness API endpoints.
8. Add shared TypeScript protocol types.
9. Show trace and pending permissions in desktop state.
10. Run all tests and quality gates.

## Verification

- Python pytest passes in isolated Bolt venv.
- pnpm test passes.
- desktop build passes.
- size, docs, and boundary checks pass.
