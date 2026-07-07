"""Simple route registrations extracted from app.py for size gate."""
from fastapi import Query
from bolt_core.checkpoint import CheckpointService
from bolt_core.app_helpers import checkpoint_workspace, string_list
from bolt_core.review_gate import ReviewChecklist
from bolt_core.tool_result_api import tool_result_dict


def register(app, harness, result_ingestion, checkpoint_service, review_gate):
    @app.get("/terminal")
    def terminal_list() -> list[dict]:
        return harness.terminal_list()

    @app.post("/terminal/{session_id}/poll")
    def terminal_poll(session_id: str) -> dict:
        return harness.terminal_poll(session_id)

    @app.post("/terminal/{session_id}/kill")
    def terminal_kill(session_id: str) -> dict:
        return harness.terminal_kill(session_id)

    @app.get("/terminal/{session_id}/output")
    def terminal_output(session_id: str) -> dict:
        return harness.terminal_output(session_id)

    @app.post("/goals")
    def create_goal(payload: dict) -> dict:
        return harness.goal_service.create_goal(payload).to_dict()

    @app.get("/goals/unfinished")
    def unfinished_goals() -> list[dict]:
        return [g.to_dict() for g in harness.goal_service.unfinished_goals()]

    @app.get("/goals/{goal_id}")
    def get_goal(goal_id: str) -> dict:
        return harness.goal_service.get_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/pause")
    def pause_goal(goal_id: str) -> dict:
        return harness.goal_service.pause_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/resume")
    def resume_goal(goal_id: str) -> dict:
        return harness.goal_service.resume_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/clear")
    def clear_goal(goal_id: str) -> dict:
        return harness.goal_service.clear_goal(goal_id).to_dict()

    @app.get("/goals/{goal_id}/evidence")
    def goal_evidence(goal_id: str) -> list[dict]:
        return [e.__dict__ for e in harness.goal_service.goal_evidence(goal_id)]

    @app.get("/goals/{goal_id}/budget")
    def goal_budget(goal_id: str) -> dict:
        return harness.goal_service.goal_budget(goal_id)

    @app.post("/conversations")
    def create_conversation(payload: dict) -> dict:
        cid = payload.get("id", f"conv_{__import__('uuid').uuid4().hex[:8]}")
        system = payload.get("system_prompt", "")
        if system:
            from bolt_core.conversation import ConversationMessage
            harness.conversation_store.add(cid, ConversationMessage(role="system", content=system))
        return {"id": cid}

    @app.get("/conversations")
    def list_conversations() -> list[str]:
        return harness.conversation_store.list_conversations()

    @app.get("/conversations/{conversation_id}")
    def get_conversation(conversation_id: str) -> list[dict]:
        return [m.to_dict() for m in harness.conversation_store.history(conversation_id)]

    @app.post("/conversations/{conversation_id}/messages")
    def add_message(conversation_id: str, payload: dict) -> dict:
        from bolt_core.conversation import ConversationMessage
        msg = ConversationMessage(role=payload.get("role", "user"),
                                  content=payload.get("content", ""),
                                  metadata=payload.get("metadata") or {})
        harness.conversation_store.add(conversation_id, msg)
        return {"status": "ok"}

    @app.get("/runs/{run_id}/timeline")
    def run_timeline(run_id: str) -> list[dict]:
        return [e.__dict__ for e in harness.trace(run_id)]

    @app.post("/checkpoints")
    def create_checkpoint(payload: dict) -> dict:
        workspace = checkpoint_workspace(payload, harness.runs, harness.workspace)
        service = CheckpointService(workspace) if workspace != harness.workspace else checkpoint_service
        checkpoint = service.create(run_id=str(payload.get("run_id", "")),
                                    goal_id=str(payload.get("goal_id", "")),
                                    changed_files=string_list(payload.get("changed_files")),
                                    constraints=string_list(payload.get("constraints")),
                                    pending_permissions=string_list(payload.get("pending_permissions")),
                                    evidence_refs=string_list(payload.get("evidence_refs")))
        checkpoint_workspaces[checkpoint.id] = workspace
        return checkpoint.to_dict()

    @app.get("/checkpoints/{checkpoint_id}")
    def load_checkpoint(checkpoint_id: str, workspace: str | None = Query(default=None)) -> dict | None:
        target = workspace or checkpoint_workspaces.get(checkpoint_id, harness.workspace)
        service = CheckpointService(target) if target != harness.workspace else checkpoint_service
        checkpoint = service.load(checkpoint_id)
        return None if checkpoint is None else checkpoint.to_dict()

    @app.post("/review/evaluate")
    def evaluate_review(payload: dict) -> dict:
        checklist = ReviewChecklist(items=string_list(payload.get("items")))
        results = payload.get("results")
        result = review_gate.evaluate(checklist, results if isinstance(results, dict) else {})
        return {"passed": result.passed, "failures": result.failures}
