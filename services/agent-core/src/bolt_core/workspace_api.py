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

logger = logging.getLogger(__name__)


def _format_time(ts: float) -> str:
    """Format a unix timestamp as a human-readable relative time string."""
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    now = datetime.datetime.now()
    delta = now - dt
    if delta.days == 0:
        return "今天"
    if delta.days == 1:
        return "昨天"
    if delta.days < 7:
        return f"{delta.days} 天前"
    return dt.strftime("%Y-%m-%d")


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
            goal_path = goals_dir / f"{goal.id}.json"
            mtime = goal_path.stat().st_mtime if goal_path.exists() else 0
            sessions.append({
                "id": goal.id,
                "title": goal.objective or "未命名目标",
                "time": _format_time(mtime),
                "status": goal.status.value,
                "_mtime": mtime,
            })

        sessions.sort(key=lambda s: s["_mtime"], reverse=True)
        visible_sessions = [
            {key: value for key, value in session.items() if key != "_mtime"}
            for session in sessions[:limit]
        ]
        return {"sessions": visible_sessions}

    return router
