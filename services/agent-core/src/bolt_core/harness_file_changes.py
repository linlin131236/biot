"""Harness file-change permission helpers."""

from dataclasses import replace
from pathlib import Path

from bolt_core.persistence.runtime_harness import persist_pending_permission
from bolt_core.tool_protocol import ToolRequest, ToolResult


def queue_file_write(harness, run_id: str, request: ToolRequest, decision, propose, encode) -> ToolResult:
    path = str(request.payload.get("path", ""))
    proposed = str(request.payload.get("proposed_content", ""))
    proposal = propose(path, proposed, harness._workspace(run_id))
    if proposal.status != "pending_review" or proposal.change is None:
        return harness._deny(request, proposal.error or "change proposal failed")
    change = proposal.change
    if not Path(path).is_absolute():
        change = replace(change, path=path)
    payload = {**request.payload, "change_set": change.__dict__}
    pending = harness.permissions.add(run_id, request, decision, payload)
    persist_pending_permission(harness, run_id, pending)
    harness._trace_log(run_id).record("change.proposed", {"request_id": request.id})
    harness._trace_log(run_id).record("permission.pending", {"request_id": request.id})
    return ToolResult.pending(request.id, encode(proposal.change))


def queue_file_patch(harness, run_id: str, request: ToolRequest, decision, guard_type, build, encode) -> ToolResult:
    path = str(request.payload.get("path", ""))
    guard = guard_type(harness._workspace(run_id))
    check = guard.check(path)
    if not check.allowed:
        return harness._deny(request, check.reason)
    target = check.path
    if not target.exists():
        return harness._deny(request, f"file not found: {path}")
    try:
        original = target.read_text(encoding="utf-8")
    except OSError as exc:
        return harness._deny(request, f"read error: {exc}")
    old_string = str(request.payload.get("old_string", ""))
    count = original.count(old_string)
    if count == 0:
        return harness._deny(request, "old_string not found in file")
    if count > 1:
        return harness._deny(request, f"old_string appears {count} times, must be unique")
    change = build(path, original, original.replace(old_string, str(request.payload.get("new_string", "")), 1))
    payload = {**request.payload, "change_set": change.__dict__}
    pending = harness.permissions.add(run_id, request, decision, payload)
    persist_pending_permission(harness, run_id, pending)
    harness._trace_log(run_id).record("change.proposed", {"request_id": request.id})
    harness._trace_log(run_id).record("permission.pending", {"request_id": request.id})
    return ToolResult.pending(request.id, encode(change))


def apply_pending_file_write(harness, item, apply) -> ToolResult:
    allowed, reason = apply(item.payload["change_set"], harness._workspace(item.run_id))
    harness._trace_log(item.run_id).record(
        "change.applied" if allowed else "change.failed", {"request_id": item.request_id},
    )
    if allowed:
        return ToolResult.executed(item.request_id, reason)
    request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
    harness._record_execution_failure(request, reason)
    return ToolResult.failed(item.request_id, reason)


def apply_pending_file_patch(harness, item, change_type, apply) -> ToolResult:
    decision = apply(change_type(**item.payload.get("change_set", {})), harness._workspace(item.run_id))
    harness._trace_log(item.run_id).record(
        "change.applied" if decision.allowed else "change.failed", {"request_id": item.request_id},
    )
    if decision.allowed:
        return ToolResult.executed(item.request_id, decision.reason)
    return ToolResult.failed(item.request_id, decision.reason)
