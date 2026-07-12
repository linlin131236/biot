"""Simple route registrations extracted from app.py for size gate."""
from fastapi import HTTPException, Query
from bolt_core.checkpoint import CheckpointService
from bolt_core.app_helpers import checkpoint_workspace, string_list
from bolt_core.review_gate import ReviewChecklist
from bolt_core.tool_result_api import tool_result_dict


def register(app, harness, result_ingestion, checkpoint_service, checkpoint_workspaces, review_gate,
             checkpoint_factory=None):
    def checkpoint_for(workspace: str):
        if workspace == harness.workspace:
            return checkpoint_service
        return checkpoint_factory(workspace) if checkpoint_factory else CheckpointService(workspace)

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
        try:
            return harness.goals.create_goal(payload).to_dict()
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/goals/unfinished")
    def unfinished_goals() -> list[dict]:
        return [g.to_dict() for g in harness.goals.unfinished_goals()]

    @app.get("/goals/{goal_id}")
    def get_goal(goal_id: str) -> dict:
        try:
            return harness.goals.get_goal(goal_id).to_dict()
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail="未找到目标") from error

    @app.post("/goals/{goal_id}/pause")
    def pause_goal(goal_id: str) -> dict:
        try:
            return harness.goals.pause_goal(goal_id).to_dict()
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail="未找到目标") from error

    @app.post("/goals/{goal_id}/resume")
    def resume_goal(goal_id: str) -> dict:
        try:
            return harness.goals.resume_goal(goal_id).to_dict()
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail="未找到目标") from error

    @app.post("/goals/{goal_id}/clear")
    def clear_goal(goal_id: str) -> dict:
        try:
            return harness.goals.clear_goal(goal_id).to_dict()
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail="未找到目标") from error

    @app.get("/goals/{goal_id}/evidence")
    def goal_evidence(goal_id: str) -> list[dict]:
        return [e.__dict__ for e in harness.goals.goal_evidence(goal_id)]

    @app.get("/goals/{goal_id}/budget")
    def goal_budget(goal_id: str) -> dict:
        return harness.goals.goal_budget(goal_id)

    @app.post("/conversations")
    def create_conversation(payload: dict) -> dict:
        try:
            cid = harness.conversations.create(payload.get("id"), payload.get("system_prompt", ""))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": cid}

    @app.get("/conversations")
    def list_conversations() -> list[str]:
        return harness.conversations.list_conversations()

    @app.get("/conversations/{conversation_id}")
    def get_conversation(conversation_id: str) -> list[dict]:
        return harness.conversations.history(conversation_id)

    @app.post("/conversations/{conversation_id}/messages")
    def add_message(conversation_id: str, payload: dict) -> dict:
        try:
            harness.conversations.add_message(
                conversation_id,
                payload.get("role", "user"),
                payload.get("content", ""),
                payload.get("metadata") or {},
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"status": "ok"}

    @app.get("/runs/{run_id}/timeline")
    def run_timeline(run_id: str) -> list[dict]:
        return [e.__dict__ for e in harness.trace(run_id)]

    @app.post("/checkpoints")
    def create_checkpoint(payload: dict) -> dict:
        workspace = checkpoint_workspace(payload, harness.runs, harness.workspace)
        service = checkpoint_for(workspace)
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
        target = checkpoint_workspaces.get(checkpoint_id, harness.workspace)
        if workspace is not None and workspace != target:
            raise HTTPException(status_code=400, detail="检查点工作区不允许由请求覆盖")
        service = checkpoint_for(target)
        checkpoint = service.load(checkpoint_id)
        return None if checkpoint is None else checkpoint.to_dict()

    @app.post("/checkpoints/{checkpoint_id}/restore")
    def restore_checkpoint(checkpoint_id: str, payload: dict,
                           workspace: str | None = Query(default=None)) -> dict:
        if not bool(payload.get("confirm_restore")):
            raise HTTPException(status_code=400, detail="恢复检查点需要用户明确确认")
        target = checkpoint_workspaces.get(checkpoint_id, harness.workspace)
        if workspace is not None and workspace != target:
            raise HTTPException(status_code=400, detail="检查点工作区不允许由请求覆盖")
        service = checkpoint_for(target)
        result = service.restore(checkpoint_id, confirm_restore=True)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="未找到检查点")
        return result

    @app.post("/review/evaluate")
    def evaluate_review(payload: dict) -> dict:
        checklist = ReviewChecklist(items=string_list(payload.get("items")))
        results = payload.get("results")
        result = review_gate.evaluate(checklist, results if isinstance(results, dict) else {})
        return {"passed": result.passed, "failures": result.failures}
