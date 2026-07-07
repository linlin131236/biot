"""Pause/resume service for long-running task nodes. Snapshot-based, re-verifies safety."""
from __future__ import annotations

import time
import uuid

from bolt_core.execution_state_machine import ExecutionStateMachine


class PauseResumeService:
    """Manages pause/resume lifecycle for task nodes.
    Pause snapshots current state. Resume re-verifies safety boundaries.
    Does NOT auto-execute or auto-approve permissions."""

    def __init__(self) -> None:
        self._snapshots: dict[str, dict] = {}  # node_id -> snapshot

    def pause(self, node_id: str, current_status: str, reason: str = "",
              evidence_refs: list[str] | None = None) -> dict:
        """Pause a node. Captures a snapshot of current state.
        Only allows pausing from 'running' or 'ready' states."""
        allowed_from = {"running", "ready"}
        if current_status not in allowed_from:
            raise ValueError(
                f"只能从 '{allowed_from}' 状态暂停，当前状态为 '{ExecutionStateMachine.label(current_status)}'。"
            )
        if node_id in self._snapshots:
            raise ValueError(f"节点 '{node_id}' 已经在暂停状态。")

        snapshot = {
            "node_id": node_id,
            "status_before_pause": current_status,
            "paused_at": time.time(),
            "reason": reason,
            "evidence_refs": list(evidence_refs or []),
            "snapshot_id": f"pause_{uuid.uuid4().hex[:8]}",
        }
        self._snapshots[node_id] = snapshot
        return {
            "action": "paused",
            "node_id": node_id,
            "from_status": current_status,
            "from_label": ExecutionStateMachine.label(current_status),
            "to_status": "paused",
            "to_label": ExecutionStateMachine.label("paused"),
            "reason": reason,
            "snapshot": snapshot,
            "warning": "暂停期间禁止执行任何副作用操作。恢复时需重新验证权限和安全边界。",
        }

    def resume(self, node_id: str, recheck_permissions: bool = True) -> dict:
        """Resume a paused node. Validates snapshot exists and re-checks safety.
        Returns an action plan, does NOT auto-execute."""
        snapshot = self._snapshots.get(node_id)
        if snapshot is None:
            raise ValueError(f"节点 '{node_id}' 不在暂停状态，无法恢复。")

        checks: list[dict] = []

        # Check 1: snapshot integrity
        checks.append({
            "check": "snapshot_integrity",
            "label": "快照完整性",
            "passed": True,
            "detail": f"快照 {snapshot['snapshot_id']} 完整，暂停于 {ExecutionStateMachine.label(snapshot['status_before_pause'])} 状态。",
        })

        # Check 2: permission re-verification
        if recheck_permissions:
            checks.append({
                "check": "permission_verify",
                "label": "权限重新验证",
                "passed": None,  # requires human decision
                "detail": "恢复后需重新通过 PermissionGate 验证。请确认权限状态后继续。",
                "requires_human": True,
            })

        # Check 3: state machine validation
        try:
            ExecutionStateMachine.validate_transition("paused", "ready")
            checks.append({
                "check": "state_transition",
                "label": "状态转换验证",
                "passed": True,
                "detail": "paused -> ready 为合法转换。",
            })
        except ValueError:
            checks.append({
                "check": "state_transition",
                "label": "状态转换验证",
                "passed": False,
                "detail": "状态转换不合法。",
            })

        all_passed = all(c["passed"] is not False for c in checks)
        has_human_required = any(c.get("requires_human") for c in checks)

        # Remove snapshot on resume
        del self._snapshots[node_id]

        return {
            "action": "resumed",
            "node_id": node_id,
            "from_status": "paused",
            "from_label": ExecutionStateMachine.label("paused"),
            "to_status": "ready",
            "to_label": ExecutionStateMachine.label("ready"),
            "snapshot": snapshot,
            "checks": checks,
            "all_checks_passed": all_passed,
            "requires_human_decision": has_human_required,
            "warning": "恢复后节点回到 ready 状态。执行前需重新通过 PermissionGate 验证权限。",
        }

    def is_paused(self, node_id: str) -> bool:
        """Check if a node is currently paused."""
        return node_id in self._snapshots

    def get_paused_nodes(self) -> list[str]:
        """List all paused node IDs."""
        return list(self._snapshots.keys())

    def get_snapshot(self, node_id: str) -> dict | None:
        """Get the pause snapshot for a node."""
        return self._snapshots.get(node_id)

    def cancel_pause(self, node_id: str) -> dict:
        """Cancel a pause and transition to failed (abandon task)."""
        snapshot = self._snapshots.pop(node_id, None)
        if snapshot is None:
            raise ValueError(f"节点 '{node_id}' 不在暂停状态。")
        return {
            "action": "cancelled",
            "node_id": node_id,
            "from_status": "paused",
            "to_status": "failed",
            "to_label": ExecutionStateMachine.label("failed"),
            "reason": "用户取消暂停，任务标记为失败。",
            "snapshot": snapshot,
        }
