"""Execution state machine API. Read-only validation; never auto-executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.execution_state_machine import ExecutionStateMachine, transition


def create_execution_state_machine_router() -> APIRouter:
    router = APIRouter(tags=["execution"])

    @router.get("/execution/state-machine/summary")
    def state_machine_summary() -> dict:
        """Return the full state machine definition: states, labels, transitions."""
        return ExecutionStateMachine.state_summary()

    @router.get("/execution/state-machine/transitions/{from_state}")
    def allowed_transitions(from_state: str) -> dict:
        """Return valid next states from a given state."""
        try:
            allowed = ExecutionStateMachine.allowed_transitions(from_state)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "from_state": from_state,
            "from_label": ExecutionStateMachine.label(from_state),
            "allowed": allowed,
            "allowed_labels": [ExecutionStateMachine.label(s) for s in allowed],
            "is_terminal": ExecutionStateMachine.is_terminal(from_state),
        }

    @router.post("/execution/state-machine/validate")
    def validate_transition(payload: dict) -> dict:
        """Validate a state transition attempt. Does NOT execute the transition."""
        from_state = str(payload.get("from_state", ""))
        to_state = str(payload.get("to_state", ""))
        node_id = str(payload.get("node_id", ""))
        reason = str(payload.get("reason", ""))
        if not from_state or not to_state:
            raise HTTPException(status_code=400, detail="from_state and to_state are required")
        try:
            return transition(node_id, from_state, to_state, reason)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
