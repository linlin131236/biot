from fastapi import APIRouter, HTTPException

from bolt_core.app_helpers import agent_loop_dict, agent_step_dict
from bolt_core.tool_protocol import ToolRequest
from bolt_core.tool_result_api import tool_result_dict


def create_harness_router(harness) -> APIRouter:
    router = APIRouter()

    @router.post("/harness/runs")
    def create_run(payload: dict) -> dict[str, str]:
        workspace = payload.get("workspace")
        try:
            run = harness.create_run(goal=str(payload.get("goal", "")), workspace=workspace if isinstance(workspace, str) and workspace else None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"id": run.id, "goal": run.goal, "workspace": run.workspace}

    @router.post("/harness/runs/{run_id}/tool-requests")
    def submit_tool(run_id: str, payload: dict) -> dict[str, str | None]:
        request = ToolRequest.create(payload["tool"], payload["operation"], payload.get("payload", {}))
        return tool_result_dict(harness.submit_tool_request(run_id, request))

    @router.post("/harness/runs/{run_id}/agent-steps")
    def run_agent_step(run_id: str) -> dict:
        return agent_step_dict(harness.run_agent_step(run_id))

    @router.post("/harness/runs/{run_id}/agent-loops")
    def run_agent_loop(run_id: str, payload: dict | None = None) -> dict:
        return agent_loop_dict(harness.run_agent_loop(run_id, int((payload or {}).get("max_steps", 50))))

    @router.get("/harness/runs/{run_id}/trace")
    def trace(run_id: str) -> list[dict]:
        return [event.__dict__ for event in harness.trace(run_id)]

    return router
