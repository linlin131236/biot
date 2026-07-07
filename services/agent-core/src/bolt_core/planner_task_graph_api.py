"""Planner task graph API. Plans only, does not auto-execute."""
from fastapi import APIRouter, HTTPException

from bolt_core.planner_task_graph import PlannerTaskGraphService


def create_planner_task_graph_router(service: PlannerTaskGraphService) -> APIRouter:
    router = APIRouter(tags=["planner"])

    @router.get("/planner/graphs")
    def list_graphs() -> list[dict]:
        """List all task graphs (summary only)."""
        return service.list_graphs()

    @router.post("/planner/graphs")
    def create_graph(payload: dict) -> dict:
        """Create a new task graph. Returns the full graph."""
        title = str(payload.get("title", ""))
        objective = str(payload.get("objective", ""))
        if not title.strip() or not objective.strip():
            raise HTTPException(status_code=400, detail="title and objective are required")
        return service.create_graph(title.strip(), objective.strip())

    @router.get("/planner/graphs/{graph_id}")
    def get_graph(graph_id: str) -> dict:
        """Get a task graph with all nodes."""
        g = service.get_graph(graph_id)
        if g is None:
            raise HTTPException(status_code=404, detail="graph not found")
        return g

    @router.post("/planner/graphs/{graph_id}/nodes")
    def add_node(graph_id: str, payload: dict) -> dict:
        """Add a node to a task graph."""
        title = str(payload.get("title", ""))
        if not title.strip():
            raise HTTPException(status_code=400, detail="node title is required")
        try:
            return service.add_node(
                graph_id=graph_id,
                title=title.strip(),
                dependencies=payload.get("dependencies"),
                risk=str(payload.get("risk", "medium")),
                owner_role=str(payload.get("owner_role", "planner")),
                evidence_refs=payload.get("evidence_refs"),
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.patch("/planner/graphs/{graph_id}/nodes/{node_id}")
    def update_node_status(graph_id: str, node_id: str, payload: dict) -> dict:
        """Update a node's status. Validates state transition rules."""
        new_status = str(payload.get("status", ""))
        if not new_status:
            raise HTTPException(status_code=400, detail="status is required")
        try:
            return service.update_node_status(graph_id, node_id, new_status)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
