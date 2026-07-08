"""Workspace API router (M152).

Provides read-only endpoints for the renderer to inspect the current
workspace and retrieve recent sessions from goal persistence.
Does NOT write to the workspace.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from bolt_core.goal_persistence import GoalPersistence
from bolt_core.goal import GoalStatus

logger = logging.getLogger(__name__)


def create_workspace_router(project_dir: str | Path | None = None) -> APIRouter:
    router = APIRouter(tags=["workspace"])
    workspace_root = Path(project_dir or Path.cwd()).resolve()

    @router.get("/workspace/status")
    def get_workspace_status() -> dict:
        """Return current workspace accessibility status."""
        accessible = workspace_root.is_dir()
        return {
            "accessible": accessible,
            "path": str(workspace_root),
        }

    @router.get("/workspace/recent-sessions")
    def get_recent_sessions(limit: int = 20) -> dict:
        """Return recent sessions from goal persistence.

        Reads goal_*.json files from .bolt/goals/ and returns
        title/time/status for each. Does NOT scan the entire disk.
        """
        goals_dir = workspace_root / ".bolt" / "goals"
        sessions: list[dict[str, Any]] = []
        if not goals_dir.is_dir():
            return {"sessions": sessions}

        persistence = GoalPersistence(str(goals_dir))
        try:
            goals = persistence.list_unfinished()
        except Exception as exc:
            logger.warning("workspace recent-sessions fallback: %s", exc)
            return {"sessions": sessions}

        for goal in goals:
            sessions.append({
                "id": goal.id,
                "title": goal.objective or "未命名目标",
                "time": "",
                "status": goal.status.value,
            })

        sessions.sort(key=lambda s: s["id"], reverse=True)
        return {"sessions": sessions[:limit]}

    return router
