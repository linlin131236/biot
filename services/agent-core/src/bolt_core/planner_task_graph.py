"""Planner task graph. Models task decomposition without auto-execution."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

VALID_STATUSES = {"pending", "in_progress", "blocked", "completed", "failed"}
VALID_RISKS = {"low", "medium", "high", "critical"}
VALID_ROLES = {"planner", "builder", "reviewer", "researcher"}
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "blocked"},
    "in_progress": {"completed", "failed", "blocked"},
    "blocked": {"pending", "in_progress"},
    "completed": set(),
    "failed": {"pending"},
}


@dataclass
class TaskNode:
    id: str
    title: str
    status: str = "pending"
    dependencies: list[str] = field(default_factory=list)
    risk: str = "medium"
    owner_role: str = "planner"
    evidence_refs: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "dependencies": list(self.dependencies),
            "risk": self.risk,
            "owner_role": self.owner_role,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> TaskNode:
        return TaskNode(
            id=data["id"],
            title=data["title"],
            status=data.get("status", "pending"),
            dependencies=list(data.get("dependencies", [])),
            risk=data.get("risk", "medium"),
            owner_role=data.get("owner_role", "planner"),
            evidence_refs=list(data.get("evidence_refs", [])),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )


@dataclass
class TaskGraph:
    id: str
    title: str
    objective: str
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "objective": self.objective,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PlannerTaskGraphService:
    """Minimal task graph model. Plans task decomposition.
    Does NOT auto-execute any node. All execution must go through
    the existing task closure + execution queue + PermissionGate pipeline.
    """

    def __init__(self) -> None:
        self._graphs: dict[str, TaskGraph] = {}

    def create_graph(self, title: str, objective: str) -> dict:
        gid = f"graph_{uuid.uuid4().hex[:8]}"
        now = time.time()
        graph = TaskGraph(id=gid, title=title, objective=objective, created_at=now, updated_at=now)
        self._graphs[gid] = graph
        return graph.to_dict()

    def list_graphs(self) -> list[dict]:
        return [
            {"id": g.id, "title": g.title, "objective": g.objective,
             "node_count": len(g.nodes), "created_at": g.created_at, "updated_at": g.updated_at}
            for g in self._graphs.values()
        ]

    def get_graph(self, graph_id: str) -> dict | None:
        g = self._graphs.get(graph_id)
        return None if g is None else g.to_dict()

    def add_node(self, graph_id: str, title: str, dependencies: list[str] | None = None,
                 risk: str = "medium", owner_role: str = "planner",
                 evidence_refs: list[str] | None = None) -> dict:
        g = self._graphs.get(graph_id)
        if g is None:
            raise ValueError(f"graph not found: {graph_id}")
        if risk not in VALID_RISKS:
            raise ValueError(f"invalid risk: {risk}, must be one of {VALID_RISKS}")
        if owner_role not in VALID_ROLES:
            raise ValueError(f"invalid owner_role: {owner_role}, must be one of {VALID_ROLES}")
        deps = list(dependencies or [])
        for dep_id in deps:
            if dep_id not in g.nodes:
                raise ValueError(f"dependency node not found in graph: {dep_id}")
        nid = f"node_{uuid.uuid4().hex[:8]}"
        now = time.time()
        node = TaskNode(
            id=nid, title=title, status="pending", dependencies=deps,
            risk=risk, owner_role=owner_role,
            evidence_refs=list(evidence_refs or []),
            created_at=now, updated_at=now,
        )
        g.nodes[nid] = node
        g.updated_at = now
        return node.to_dict()

    def update_node_status(self, graph_id: str, node_id: str, new_status: str) -> dict:
        g = self._graphs.get(graph_id)
        if g is None:
            raise ValueError(f"graph not found: {graph_id}")
        node = g.nodes.get(node_id)
        if node is None:
            raise ValueError(f"node not found: {node_id}")
        if new_status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {new_status}, must be one of {VALID_STATUSES}")

        allowed = STATUS_TRANSITIONS.get(node.status, set())
        if new_status not in allowed and node.status != new_status:
            raise ValueError(
                f"invalid status transition: {node.status} -> {new_status}. "
                f"Allowed transitions: {allowed or 'none (terminal)'}"
            )

        # Blocked check: all dependencies must be completed
        if new_status == "in_progress":
            for dep_id in node.dependencies:
                dep = g.nodes.get(dep_id)
                if dep is None or dep.status != "completed":
                    raise ValueError(
                        f"cannot start node '{node_id}': dependency '{dep_id}' is not completed"
                    )

        now = time.time()
        node.status = new_status
        node.updated_at = now
        g.updated_at = now
        return node.to_dict()
