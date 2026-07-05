from fastapi import FastAPI, Query

from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest, ToolResult


def create_app() -> FastAPI:
    app = FastAPI(title="Bolt Agent Core")
    harness = Harness(workspace="D:/Bolt/Bolt")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "bolt-agent-core"}

    @app.get("/context/p0")
    def p0_context() -> dict[str, list]:
        return harness.p0_context()

    @app.post("/harness/runs")
    def create_run(payload: dict) -> dict[str, str]:
        run = harness.create_run(goal=str(payload.get("goal", "")))
        return {"id": run.id, "goal": run.goal}

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
