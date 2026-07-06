"""Task closure API router — separate from main app to keep app.py under 300 lines."""
from fastapi import APIRouter, HTTPException

from bolt_core.task_closure import TaskClosureStatus, task_templates as _task_templates_fn
from bolt_core.task_closure_service import TaskClosureService

router = APIRouter(prefix="/task-closures", tags=["task-closure"])
_tc_service = TaskClosureService()


@router.get("/templates")
def get_task_templates() -> list[dict]:
    """Return available task templates with Chinese labels."""
    return _task_templates_fn()


@router.post("")
def create_task_closure(payload: dict) -> dict:
    """Create a new task closure record. Does NOT execute any tools."""
    objective = str(payload.get("objective", ""))
    template_id = str(payload.get("template_id", "bugfix"))
    run_id = payload.get("run_id")
    goal_id = payload.get("goal_id")
    if not objective:
        raise HTTPException(status_code=400, detail="objective 不能为空")
    allowed_templates = {item["id"] for item in _task_templates_fn()}
    if template_id not in allowed_templates:
        raise HTTPException(status_code=400, detail="未知任务模板")
    closure = _tc_service.start(objective, template_id, run_id, goal_id)
    return _tc_service.to_dict(closure.id)


@router.get("/{closure_id}")
def get_task_closure(closure_id: str) -> dict:
    """Get closure by id. Returns 404 if not found."""
    closure = _tc_service.load(closure_id)
    if closure is None:
        raise HTTPException(status_code=404, detail="任务闭环不存在")
    return _tc_service.to_dict(closure_id)


@router.post("/{closure_id}/events")
def add_closure_event(closure_id: str, payload: dict) -> dict:
    """Record an event (transition, command, file_change, permission). Does NOT execute."""
    closure = _tc_service.load(closure_id)
    if closure is None:
        raise HTTPException(status_code=404, detail="任务闭环不存在")
    event_type = str(payload.get("type", ""))
    if event_type == "transition":
        target = str(payload.get("target", ""))
        try:
            _tc_service.transition(closure_id, TaskClosureStatus(target))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif event_type == "command":
        _tc_service.record_command(closure_id, str(payload.get("command", "")), str(payload.get("result", "")))
    elif event_type == "file_change":
        _tc_service.record_file_change(closure_id, str(payload.get("path", "")))
    elif event_type == "permission":
        _tc_service.record_permission(closure_id, str(payload.get("id", "")))
    else:
        raise HTTPException(status_code=400, detail=f"未知事件类型: {event_type}")
    return _tc_service.to_dict(closure_id)


@router.post("/{closure_id}/review")
def add_closure_review(closure_id: str, payload: dict) -> dict:
    """Record a review summary. Does NOT execute."""
    closure = _tc_service.load(closure_id)
    if closure is None:
        raise HTTPException(status_code=404, detail="任务闭环不存在")
    summary = str(payload.get("summary", ""))
    passed = bool(payload.get("passed", False))
    _tc_service.record_review(closure_id, summary, passed)
    return _tc_service.to_dict(closure_id)
