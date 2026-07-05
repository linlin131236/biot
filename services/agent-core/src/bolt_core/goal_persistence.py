import json
import re
from pathlib import Path

from bolt_core.goal import Goal, GoalStatus

GOAL_ID_PATTERN = re.compile(r"^goal_[a-f0-9]{8}$")


class GoalPersistence:
    def __init__(self, storage_dir: str) -> None:
        self._dir = Path(storage_dir)
        self._lock = __import__("threading").Lock()

    def _validate_id(self, goal_id: str) -> None:
        if not GOAL_ID_PATTERN.match(goal_id):
            raise ValueError(f"Invalid goal_id: {goal_id}")

    def save(self, goal: Goal) -> None:
        self._validate_id(goal.id)
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self._dir / f"{goal.id}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(goal.to_dict(), indent=2), encoding="utf-8")
            tmp.replace(path)

    def load(self, goal_id: str) -> Goal:
        self._validate_id(goal_id)
        path = self._dir / f"{goal_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Goal not found: {goal_id}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Goal file corrupt: {goal_id}: {e}") from e
        return Goal.from_dict(data)

    def check_conflicts(self, goal_id: str) -> list[str]:
        goal = self.load(goal_id)
        conflicts = []
        workspace = Path(goal.workspace)
        for rel_path, expected in goal.file_snapshot.items():
            full_path = workspace / rel_path
            if full_path.exists():
                if full_path.read_text(encoding="utf-8") != expected:
                    conflicts.append(f"{rel_path}: content has changed")
        return conflicts

    def list_unfinished(self) -> list[Goal]:
        if not self._dir.exists():
            return []
        results = []
        for path in self._dir.glob("goal_*.json"):
            try:
                goal = Goal.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, Exception):
                continue
            if goal.status in (GoalStatus.PENDING, GoalStatus.RUNNING, GoalStatus.PAUSED):
                results.append(goal)
        return results
