"""Task closure API router — separate from main app to keep app.py under 300 lines."""
from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from bolt_core.task_closure import TaskClosureStatus, task_templates as _task_templates_fn
from bolt_core.task_closure_service import TaskClosureService


def create_task_closure_router(
    service: TaskClosureService,
    run_exists: Callable[[str], bool] | None = None,
    goal_exists: Callable[[str], bool] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/task-closures", tags=["task-closure"])

    @router.get("/templates")
    def get_task_templates() -> list[dict]:
        """Return available task templates with Chinese labels."""
        return _task_templates_fn()

    @router.post("")
    def create_task_closure(payload: dict) -> dict:
        """Create a new task closure record. Does NOT execute any tools."""
        objective = str(payload.get("objective", ""))
        template_id = str(payload.get("template_id", "bugfix"))
        run_id = _optional_id(payload.get("run_id"))
        goal_id = _optional_id(payload.get("goal_id"))
        if not objective:
            raise HTTPException(status_code=400, detail="objective 不能为空")
        if template_id not in _allowed_templates():
            raise HTTPException(status_code=400, detail="未知任务模板")
        if run_id is not None and run_exists is not None and not run_exists(run_id):
            raise HTTPException(status_code=404, detail="运行不存在")
        if goal_id is not None and goal_exists is not None and not goal_exists(goal_id):
            raise HTTPException(status_code=404, detail="目标不存在")
        closure = service.start(objective, template_id, run_id, goal_id)
        return service.to_dict(closure.id)

    @router.get("/by-run/{run_id}")
    def get_task_closure_by_run(run_id: str) -> dict:
        closure = service.find_by_run(run_id)
        if closure is None:
            raise HTTPException(status_code=404, detail="任务闭环不存在")
        return service.to_dict(closure.id)

    @router.get("/by-goal/{goal_id}")
    def get_task_closure_by_goal(goal_id: str) -> dict:
        closure = service.find_by_goal(goal_id)
        if closure is None:
            raise HTTPException(status_code=404, detail="任务闭环不存在")
        return service.to_dict(closure.id)

    @router.get("/{closure_id}")
    def get_task_closure(closure_id: str) -> dict:
        """Get closure by id. Returns 404 if not found."""
        _require_closure(service, closure_id)
        return service.to_dict(closure_id)

    @router.get("/{closure_id}/verification-plan")
    def get_task_closure_verification_plan(closure_id: str) -> dict:
        """Get verification plan. Does NOT execute commands."""
        _require_closure(service, closure_id)
        return service.verification_plan(closure_id)

    @router.get("/{closure_id}/assessment")
    def get_task_closure_assessment(closure_id: str) -> dict:
        """Assess completion without mutating closure."""
        _require_closure(service, closure_id)
        return service.assess_completion(closure_id)

    @router.get("/{closure_id}/result-summary")
    def get_task_closure_result_summary(closure_id: str) -> dict:
        """Synthesize a structured result summary from closure data."""
        _require_closure(service, closure_id)
        return service.result_summary(closure_id)

    @router.post("/{closure_id}/assessment")
    def update_task_closure_assessment(closure_id: str) -> dict:
        """Update closure from recorded evidence only."""
        _require_closure(service, closure_id)
        service.update_assessment(closure_id)
        return service.to_dict(closure_id)

    @router.post("/{closure_id}/bind-run")
    def bind_task_closure_run(closure_id: str, payload: dict) -> dict:
        _require_closure(service, closure_id)
        run_id = str(payload.get("run_id", ""))
        if not run_id:
            raise HTTPException(status_code=400, detail="run_id 不能为空")
        if run_exists is not None and not run_exists(run_id):
            raise HTTPException(status_code=404, detail="运行不存在")
        service.bind_run(closure_id, run_id)
        return service.to_dict(closure_id)

    @router.post("/{closure_id}/bind-goal")
    def bind_task_closure_goal(closure_id: str, payload: dict) -> dict:
        _require_closure(service, closure_id)
        goal_id = str(payload.get("goal_id", ""))
        if not goal_id:
            raise HTTPException(status_code=400, detail="goal_id 不能为空")
        if goal_exists is not None and not goal_exists(goal_id):
            raise HTTPException(status_code=404, detail="目标不存在")
        service.bind_goal(closure_id, goal_id)
        return service.to_dict(closure_id)

    @router.post("/{closure_id}/events")
    def add_closure_event(closure_id: str, payload: dict) -> dict:
        """Record an event (transition, command, file_change, permission). Does NOT execute."""
        _require_closure(service, closure_id)
        event_type = str(payload.get("type", ""))
        if event_type == "transition":
            target = str(payload.get("target", ""))
            try:
                service.transition(closure_id, TaskClosureStatus(target))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        elif event_type == "command":
            service.record_command(closure_id, str(payload.get("command", "")), str(payload.get("result", "")))
        elif event_type == "file_change":
            service.record_file_change(closure_id, str(payload.get("path", "")))
        elif event_type == "permission":
            service.record_permission(closure_id, str(payload.get("id", "")))
        else:
            raise HTTPException(status_code=400, detail=f"未知事件类型: {event_type}")
        return service.to_dict(closure_id)

    @router.post("/{closure_id}/review")
    def add_closure_review(closure_id: str, payload: dict) -> dict:
        """Record a review summary. Does NOT execute."""
        _require_closure(service, closure_id)
        summary = str(payload.get("summary", ""))
        passed = bool(payload.get("passed", False))
        service.record_review(closure_id, summary, passed)
        return service.to_dict(closure_id)

    return router


def _allowed_templates() -> set[str]:
    return {str(item["id"]) for item in _task_templates_fn()}


def _optional_id(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _require_closure(service: TaskClosureService, closure_id: str) -> None:
    if service.load(closure_id) is None:
        raise HTTPException(status_code=404, detail="任务闭环不存在")


_default_service = TaskClosureService()
router = create_task_closure_router(_default_service)
