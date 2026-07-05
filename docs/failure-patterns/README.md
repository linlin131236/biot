# Failure Patterns

This directory stores durable lessons from real tool and harness failures.

Each generated entry should use these sections:

- `Trigger`: tool, operation, and failure class.
- `Symptom`: observable result from the failed run.
- `Root Cause`: known or suspected cause.
- `Repair`: current repair status or fix.
- `Do Not Repeat`: the next-run constraint.
- `Source`: memory or tool request source id.

Document gardener proposals must enter through `file.write` and ChangeSet approval before files appear here.
