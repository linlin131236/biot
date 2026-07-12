"""Repository persistence helpers for TaskClosureService."""

from bolt_core.persistence.closure_payload import redacted_closure_payload
from bolt_core.task_closure import TaskClosure


def restore(service) -> None:
    from bolt_core.task_closure_service import TaskClosureRecord
    for row in service._repository.list_closures(service._workspace_id):
        payload = row["payload"]
        closure = TaskClosure(
            **{key: payload.get(key) for key in (
                "objective", "template_id", "run_id", "goal_id", "plan_summary",
                "changed_files", "commands", "command_results", "permission_request_ids",
                "retry_count", "review_summary", "next_action", "created_at",
            )}, id=row["id"], status=row["status"],
        )
        service._store[closure.id] = TaskClosureRecord(closure, payload.get("events", []))
        service._revisions[closure.id] = row["revision"]


def save(service) -> None:
    for record in service._store.values():
        closure = record.closure
        payload = redacted_closure_payload(closure, record.events)
        revision = service._revisions.get(closure.id)
        if revision is None:
            service._repository.create_closure(
                closure.id, service._workspace_id, closure.status, payload,
            )
            service._revisions[closure.id] = 0
            continue
        updated = service._repository.update_closure(
            closure.id, expected_revision=revision,
            status=closure.status, payload=payload,
        )
        service._revisions[closure.id] = updated["revision"]
