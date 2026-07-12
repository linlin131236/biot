from bolt_core.harness import Harness
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_result_api import tool_result_dict


def goal_exists(harness: Harness, goal_id: str) -> bool:
    try:
        harness.goals.get_goal(goal_id)
        return True
    except Exception:
        return False


def permission_bridge_target(record, closures: TaskClosureService, harness: Harness, fallback_run_id: str) -> tuple[str, str]:
    if record.run_id and record.permission_workspace and record.run_id not in harness.runs:
        harness.register_internal_run(record.run_id, "恢复人工执行权限", record.permission_workspace)
        return record.run_id, record.permission_workspace
    closure = closures.load(record.closure_id)
    run_id = closure.run_id if closure is not None and closure.run_id in harness.runs else fallback_run_id
    return run_id, harness.runs[run_id].workspace


def agent_step_dict(result) -> dict:
    return {
        "status": result.status,
        "model_output": result.model_output,
        "tool_result": None if result.tool_result is None else tool_result_dict(result.tool_result),
        "error": result.error,
    }


def agent_loop_dict(result) -> dict:
    return {
        "status": result.status,
        "steps": result.steps,
        "last_step": None if result.last_step is None else agent_step_dict(result.last_step),
        "error": result.error,
    }


def string_list(value) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def checkpoint_workspace(payload: dict, runs: dict, default_workspace: str) -> str:
    run = runs.get(str(payload.get("run_id", "")))
    return run.workspace if run is not None else default_workspace
