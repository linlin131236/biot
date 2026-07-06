from pathlib import Path

from fastapi import FastAPI, Query

from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest, ToolResult


def create_app() -> FastAPI:
    app = FastAPI(title="Bolt Agent Core")
    harness = Harness(workspace=str(Path.cwd()))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "bolt-agent-core"}

    @app.get("/context/p0")
    def p0_context() -> dict[str, list]:
        return harness.p0_context()

    @app.post("/harness/runs")
    def create_run(payload: dict) -> dict[str, str]:
        workspace = payload.get("workspace")
        run = harness.create_run(goal=str(payload.get("goal", "")), workspace=workspace if isinstance(workspace, str) and workspace else None)
        return {"id": run.id, "goal": run.goal, "workspace": run.workspace}

    @app.post("/harness/runs/{run_id}/tool-requests")
    def submit_tool(run_id: str, payload: dict) -> dict[str, str | None]:
        request = ToolRequest.create(payload["tool"], payload["operation"], payload.get("payload", {}))
        result = harness.submit_tool_request(run_id, request)
        return _tool_result_dict(result)

    @app.post("/harness/runs/{run_id}/agent-steps")
    def run_agent_step(run_id: str) -> dict:
        result = harness.run_agent_step(run_id)
        return _agent_step_dict(result)

    @app.post("/harness/runs/{run_id}/agent-loops")
    def run_agent_loop(run_id: str, payload: dict | None = None) -> dict:
        result = harness.run_agent_loop(run_id, int((payload or {}).get("max_steps", 3)))
        return _agent_loop_dict(result)

    @app.get("/harness/runs/{run_id}/trace")
    def trace(run_id: str) -> list[dict]:
        return [event.__dict__ for event in harness.trace(run_id)]

    @app.get("/memory")
    def memory() -> dict:
        return harness.memory_snapshot()

    @app.post("/memory")
    def record_memory(payload: dict) -> dict:
        return harness.record_memory(payload).__dict__

    @app.get("/memory/records")
    def memory_records(kind: str | None = Query(default=None), scope: str | None = Query(default=None), status: str | None = Query(default=None), query: str | None = Query(default=None)) -> list[dict]:
        return [record.__dict__ for record in harness.query_memory(kind, scope, status, query)]

    @app.post("/memory/{memory_id}/resolve")
    def resolve_memory(memory_id: str) -> dict:
        return harness.resolve_memory(memory_id).__dict__

    @app.post("/memory/consolidate")
    def consolidate_memory() -> dict:
        return harness.consolidate_memory().__dict__

    @app.post("/maintenance/document-gardener/runs/{run_id}")
    def run_document_gardener(run_id: str) -> dict[str, str | None]:
        result = harness.run_document_gardener(run_id)
        return _tool_result_dict(result)

    @app.get("/memory/p0")
    def memory_p0() -> dict[str, list]:
        return harness.p0_context()

    @app.get("/model/settings")
    def model_settings() -> dict:
        return harness.model_settings_status().__dict__

    @app.post("/model/settings")
    def update_model_settings(payload: dict) -> dict:
        return harness.update_model_settings(payload).__dict__

    @app.get("/permissions/pending")
    def pending_permissions() -> list[dict]:
        return [item.__dict__ for item in harness.pending_permissions()]

    @app.post("/permissions/{request_id}/approve")
    def approve_permission(request_id: str) -> dict[str, str | None]:
        result = harness.approve_permission(request_id)
        return _tool_result_dict(result)

    @app.post("/permissions/{request_id}/reject")
    def reject_permission(request_id: str) -> dict[str, str | None]:
        result = harness.reject_permission(request_id)
        return _tool_result_dict(result)

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
        msg = ConversationMessage(
            role=payload.get("role", "user"),
            content=payload.get("content", ""),
            metadata=payload.get("metadata") or {},
        )
        harness.conversation_store.add(conversation_id, msg)
        return {"status": "ok"}

    @app.post("/runs/{run_id}/steering")
    def steer_run(run_id: str, payload: dict) -> dict:
        from bolt_core.conversation import ConversationMessage
        cid = f"run_{run_id}"
        msg = ConversationMessage(
            role="user",
            content=payload.get("content", ""),
            metadata={"steering": True, "run_id": run_id},
        )
        harness.conversation_store.add(cid, msg)
        return {"status": "injected"}

    @app.get("/runs/{run_id}/timeline")
    def run_timeline(run_id: str) -> list[dict]:
        events = harness.trace(run_id)
        return [e.__dict__ for e in events]

    return app


def _agent_step_dict(result) -> dict:
    return {
        "status": result.status,
        "model_output": result.model_output,
        "tool_result": None if result.tool_result is None else _tool_result_dict(result.tool_result),
        "error": result.error,
    }


def _agent_loop_dict(result) -> dict:
    return {
        "status": result.status,
        "steps": result.steps,
        "last_step": None if result.last_step is None else _agent_step_dict(result.last_step),
        "error": result.error,
    }


def _tool_result_dict(result: ToolResult) -> dict[str, str | None]:
    return {
        "request_id": result.request_id,
        "status": result.status,
        "reason": result.reason,
        "output": result.output,
        "error": result.error,
    }


app = create_app()
