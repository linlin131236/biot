"""Secret-safe serialization for task-closure repository records."""

from bolt_core.evidence_redactor import redact


def redacted_closure_payload(closure, events: list[dict]) -> dict:
    return {
        "objective": redact(closure.objective), "template_id": closure.template_id,
        "run_id": closure.run_id, "goal_id": closure.goal_id,
        "plan_summary": redact(closure.plan_summary),
        "changed_files": list(closure.changed_files),
        "commands": [redact(value) for value in closure.commands],
        "command_results": [redact(value) for value in closure.command_results],
        "permission_request_ids": list(closure.permission_request_ids),
        "retry_count": closure.retry_count, "review_summary": redact(closure.review_summary),
        "next_action": redact(closure.next_action), "created_at": closure.created_at,
        "events": [redacted_event(event) for event in events],
    }


def redacted_event(event: dict) -> dict:
    return {key: redact(value) if isinstance(value, str) else value for key, value in event.items()}
