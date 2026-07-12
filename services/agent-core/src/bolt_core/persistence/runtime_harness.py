"""Repository-backed Harness runtime lifecycle helpers."""

from bolt_core.harness_state import HarnessRun
from bolt_core.permission_queue import PendingPermission
from bolt_core.persistence.errors import RuntimeSessionActionError
from bolt_core.persistence.runtime_trace import RepositoryTraceLog


def register_run(harness, run: HarnessRun):
    if harness.persistence is None or run.id == "run_execution_bridge":
        return harness._state.register(run)
    trace = RepositoryTraceLog(run.id, harness.persistence, run.id)
    with harness._state.lock:
        harness._state.runs[run.id], harness._state.traces[run.id] = run, trace
    return trace


def ensure_runtime(harness, run: HarnessRun) -> None:
    if harness.persistence is None or run.id == "run_execution_bridge":
        return
    task_id = f"task_{run.id}"
    try:
        harness.persistence.load_task(task_id)
    except KeyError:
        harness.persistence.create_runtime_task(
            task_id, harness._workspace_id, run.id, "bolt-native", run.id,
            {"run_id": run.id, "goal": run.goal, "workspace": run.workspace},
        )


def restore_runs(harness) -> None:
    if harness.persistence is None:
        return
    for record in harness.persistence.list_runtime_sessions(harness._workspace_id):
        payload = record["task_payload"]
        run_id = str(record["id"])
        run = HarnessRun(run_id, str(payload.get("goal", "")), str(payload.get("workspace", harness.workspace)))
        trace = RepositoryTraceLog(run_id, harness.persistence, run_id)
        with harness._state.lock:
            harness._state.runs[run_id], harness._state.traces[run_id] = run, trace
        pending_items = payload.get("pending_permissions", [])
        if isinstance(pending_items, list):
            for pending in pending_items:
                if isinstance(pending, dict):
                    harness.permissions.restore(PendingPermission(**pending))


def update_runtime(harness, run_id: str, status: str, payload: dict | None = None) -> None:
    if harness.persistence is None or run_id == "run_execution_bridge":
        return
    task = harness.persistence.load_task(f"task_{run_id}")
    harness.persistence.update_runtime_task(
        f"task_{run_id}", run_id, task["revision"], status, payload,
    )


def finish_runtime(harness, run_id: str, status: str) -> None:
    update_runtime(harness, run_id, status)


def assert_run_open(harness, run_id: str) -> None:
    if harness.persistence is not None and run_id != "run_execution_bridge":
        if not harness.persistence.runtime_session_is_open(run_id):
            raise RuntimeSessionActionError("runtime session is closed")


def persist_pending_permission(harness, run_id: str, item: PendingPermission) -> None:
    if harness.persistence is None or run_id == "run_execution_bridge":
        return
    task = harness.persistence.load_task(f"task_{run_id}")
    pending = task["payload"].get("pending_permissions", [])
    pending = [
        entry for entry in pending
        if isinstance(entry, dict) and entry.get("request_id") != item.request_id
    ] if isinstance(pending, list) else []
    pending.append(item.__dict__)
    update_runtime(harness, run_id, "waiting_approval", {
        **task["payload"], "pending_permissions": pending,
    })


def clear_pending_permission(harness, run_id: str, request_id: str) -> None:
    if harness.persistence is None or run_id == "run_execution_bridge":
        return
    task = harness.persistence.load_task(f"task_{run_id}")
    payload = dict(task["payload"])
    pending = payload.get("pending_permissions", [])
    payload["pending_permissions"] = [
        item for item in pending
        if isinstance(item, dict) and item.get("request_id") != request_id
    ] if isinstance(pending, list) else []
    if not payload["pending_permissions"]:
        payload.pop("pending_permissions", None)
    status = "waiting_approval" if payload.get("pending_permissions") else "running"
    update_runtime(harness, run_id, status, payload)


def finish_step_runtime(harness, run_id: str, status: str) -> None:
    if harness.persistence is not None and run_id != "run_execution_bridge":
        finish_runtime(harness, run_id, "completed" if status == "completed" else "failed")
