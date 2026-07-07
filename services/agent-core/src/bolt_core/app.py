from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from bolt_core.checkpoint import CheckpointService
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_handoff_api import create_execution_handoff_router
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.execution_queue_api import create_execution_queue_router
from bolt_core.execution_result_ingestion import ExecutionResultIngestionService
from bolt_core.app_helpers import agent_loop_dict, agent_step_dict, checkpoint_workspace, goal_exists, permission_bridge_target, string_list
from bolt_core.harness import Harness
from bolt_core.review_gate import ReviewChecklist, ReviewGate
from bolt_core.task_closure_api import create_task_closure_router
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolRequest
from bolt_core.tool_result_api import tool_result_dict

from bolt_core.execution_audit_store import ExecutionAuditStore, ExecutionAuditStoreError, execution_audit_path as resolve_execution_audit_path
from bolt_core.execution_audit_diagnostics import ExecutionAuditDiagnosticsService
from bolt_core.execution_audit_diagnostics_api import create_execution_audit_diagnostics_router
from bolt_core.execution_audit_integrity import ExecutionAuditIntegrityService
from bolt_core.execution_audit_integrity_api import create_execution_audit_integrity_router
from bolt_core.execution_audit_timeline import ExecutionAuditTimelineService
from bolt_core.execution_audit_timeline_api import create_execution_audit_timeline_router
from bolt_core.execution_state_machine_api import create_execution_state_machine_router
from bolt_core.local_release_checklist import LocalReleaseChecklistService
from bolt_core.local_release_checklist_api import create_local_release_checklist_router
from bolt_core.planner_task_graph import PlannerTaskGraphService
from bolt_core.planner_task_graph_api import create_planner_task_graph_router
from bolt_core.recovery_policy import RecoveryPolicyService
from bolt_core.recovery_policy_api import create_recovery_policy_router
from bolt_core.tool_selection_policy_api import create_tool_selection_policy_router
from bolt_core.failure_classifier_api import create_failure_classifier_router
from bolt_core.safe_retry_loop_api import create_safe_retry_loop_router
from bolt_core.code_map_index_api import create_code_map_index_router
from bolt_core.project_profile_api import create_project_profile_router
from bolt_core.long_task_recovery_dogfood_api import create_long_task_recovery_dogfood_router
from bolt_core.agent_budget_api import create_agent_budget_router
from bolt_core.human_steering_api import create_human_steering_router
from bolt_core.pause_resume_api import create_pause_resume_router
from bolt_core.decision_memory_api import create_decision_memory_router
from bolt_core.failure_memory_index_api import create_failure_memory_index_router
from bolt_core.user_preference_memory_api import create_user_preference_memory_router
from bolt_core.context_compaction_api import create_context_compaction_router
from bolt_core.thread_handoff_summary_api import create_thread_handoff_summary_router
from bolt_core.memory_permission_boundary_api import create_memory_permission_boundary_router
from bolt_core.memory_dogfood_api import create_memory_dogfood_router
from bolt_core.release_readiness import ReleaseReadinessService
from bolt_core.release_readiness_api import create_release_readiness_router


def create_app(execution_audit_path: str | Path | None = None, project_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Bolt Agent Core")
    audit_store = ExecutionAuditStore(resolve_execution_audit_path(execution_audit_path, Path.cwd()))
    try:
        task_closure_service = TaskClosureService(audit_store)
        execution_queue_service = ExecutionQueueService(audit_store)
        execution_handoff_service = ExecutionHandoffService(audit_store)
    except ExecutionAuditStoreError:
        task_closure_service = TaskClosureService(None)
        execution_queue_service = ExecutionQueueService(None)
        execution_handoff_service = ExecutionHandoffService(None)
    harness = Harness(workspace=str(Path.cwd()), task_closure_service=task_closure_service)
    bridge_run_id = "run_execution_bridge"
    harness.register_internal_run(bridge_run_id, "申请人工执行权限")
    permission_bridge = ExecutionPermissionBridgeService(execution_handoff_service, harness.permissions, lambda record: permission_bridge_target(record, task_closure_service, harness, bridge_run_id))
    result_ingestion = ExecutionResultIngestionService(execution_handoff_service, execution_queue_service, task_closure_service)
    timeline_service = ExecutionAuditTimelineService(execution_queue_service, execution_handoff_service, task_closure_service)
    diagnostics_service = ExecutionAuditDiagnosticsService(execution_queue_service, execution_handoff_service, harness.permissions, task_closure_service)
    integrity_service = ExecutionAuditIntegrityService(audit_store)
    readiness_service = ReleaseReadinessService(str(project_dir or Path.cwd()), audit_store)
    local_checklist_service = LocalReleaseChecklistService(str(project_dir or Path.cwd()), audit_store)
    recovery_policy_service = RecoveryPolicyService()
    planner_service = PlannerTaskGraphService()
    checkpoint_service = CheckpointService(harness.workspace)
    checkpoint_workspaces: dict[str, str] = {}
    review_gate = ReviewGate()
    app.include_router(create_task_closure_router(
        task_closure_service,
        run_exists=lambda run_id: run_id in harness.runs,
        goal_exists=lambda goal_id: goal_exists(harness, goal_id),
    ))
    app.include_router(create_execution_queue_router(execution_queue_service, task_closure_service))
    app.include_router(create_execution_handoff_router(execution_handoff_service, execution_queue_service, permission_bridge))
    app.include_router(create_execution_audit_timeline_router(timeline_service, task_closure_service))
    app.include_router(create_execution_audit_diagnostics_router(diagnostics_service))
    app.include_router(create_execution_audit_integrity_router(integrity_service))
    app.include_router(create_release_readiness_router(readiness_service))
    app.include_router(create_local_release_checklist_router(local_checklist_service))
    app.include_router(create_recovery_policy_router(recovery_policy_service))
    app.include_router(create_planner_task_graph_router(planner_service))
    app.include_router(create_execution_state_machine_router())
    app.include_router(create_tool_selection_policy_router())
    app.include_router(create_failure_classifier_router())
    app.include_router(create_safe_retry_loop_router())
    app.include_router(create_code_map_index_router())
    app.include_router(create_project_profile_router())
    app.include_router(create_long_task_recovery_dogfood_router())
    app.include_router(create_agent_budget_router())
    app.include_router(create_human_steering_router())
    app.include_router(create_pause_resume_router())
    app.include_router(create_decision_memory_router())
    app.include_router(create_failure_memory_index_router())
    app.include_router(create_user_preference_memory_router())
    app.include_router(create_context_compaction_router())
    app.include_router(create_thread_handoff_summary_router())
    app.include_router(create_memory_permission_boundary_router())
    app.include_router(create_memory_dogfood_router())

    @app.get("/health")
    def health() -> dict[str, str]: return {"status": "ok", "service": "bolt-agent-core"}

    @app.get("/context/p0")
    def p0_context() -> dict[str, list]: return harness.p0_context()

    @app.post("/harness/runs")
    def create_run(payload: dict) -> dict[str, str]:
        workspace = payload.get("workspace")
        run = harness.create_run(goal=str(payload.get("goal", "")), workspace=workspace if isinstance(workspace, str) and workspace else None)
        return {"id": run.id, "goal": run.goal, "workspace": run.workspace}

    @app.post("/harness/runs/{run_id}/tool-requests")
    def submit_tool(run_id: str, payload: dict) -> dict[str, str | None]:
        request = ToolRequest.create(payload["tool"], payload["operation"], payload.get("payload", {}))
        result = harness.submit_tool_request(run_id, request)
        return tool_result_dict(result)

    @app.post("/harness/runs/{run_id}/agent-steps")
    def run_agent_step(run_id: str) -> dict:
        result = harness.run_agent_step(run_id)
        return agent_step_dict(result)

    @app.post("/harness/runs/{run_id}/agent-loops")
    def run_agent_loop(run_id: str, payload: dict | None = None) -> dict:
        result = harness.run_agent_loop(run_id, int((payload or {}).get("max_steps", 3)))
        return agent_loop_dict(result)

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
        return tool_result_dict(result)

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
        result_ingestion.ingest(result)
        return tool_result_dict(result)

    @app.post("/permissions/{request_id}/reject")
    def reject_permission(request_id: str) -> dict[str, str | None]:
        result = harness.reject_permission(request_id)
        result_ingestion.ingest(result)
        return tool_result_dict(result)

    @app.get("/terminal")
    def terminal_list() -> list[dict]:
        return harness.terminal_list()

    @app.post("/terminal/{session_id}/poll")
    def terminal_poll(session_id: str) -> dict:
        return harness.terminal_poll(session_id)

    @app.post("/terminal/{session_id}/kill")
    def terminal_kill(session_id: str) -> dict:
        return harness.terminal_kill(session_id)

    @app.get("/terminal/{session_id}/output")
    def terminal_output(session_id: str) -> dict:
        return harness.terminal_output(session_id)

    @app.post("/goals")
    def create_goal(payload: dict) -> dict:
        return harness.goal_service.create_goal(payload).to_dict()

    @app.get("/goals/unfinished")
    def unfinished_goals() -> list[dict]:
        return [g.to_dict() for g in harness.goal_service.unfinished_goals()]

    @app.get("/goals/{goal_id}")
    def get_goal(goal_id: str) -> dict:
        return harness.goal_service.get_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/pause")
    def pause_goal(goal_id: str) -> dict:
        return harness.goal_service.pause_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/resume")
    def resume_goal(goal_id: str) -> dict:
        return harness.goal_service.resume_goal(goal_id).to_dict()

    @app.post("/goals/{goal_id}/clear")
    def clear_goal(goal_id: str) -> dict:
        return harness.goal_service.clear_goal(goal_id).to_dict()

    @app.get("/goals/{goal_id}/evidence")
    def goal_evidence(goal_id: str) -> list[dict]:
        return [e.__dict__ for e in harness.goal_service.goal_evidence(goal_id)]

    @app.get("/goals/{goal_id}/budget")
    def goal_budget(goal_id: str) -> dict:
        return harness.goal_service.goal_budget(goal_id)

    @app.post("/conversations")
    def create_conversation(payload: dict) -> dict:
        cid = payload.get("id", f"conv_{__import__('uuid').uuid4().hex[:8]}")
        system = payload.get("system_prompt", "")
        if system:
            from bolt_core.conversation import ConversationMessage
            harness.conversation_store.add(cid, ConversationMessage(role="system", content=system))
        return {"id": cid}

    @app.get("/conversations")
    def list_conversations() -> list[str]:
        return harness.conversation_store.list_conversations()

    @app.get("/conversations/{conversation_id}")
    def get_conversation(conversation_id: str) -> list[dict]:
        return [m.to_dict() for m in harness.conversation_store.history(conversation_id)]

    @app.post("/conversations/{conversation_id}/messages")
    def add_message(conversation_id: str, payload: dict) -> dict:
        from bolt_core.conversation import ConversationMessage
        msg = ConversationMessage(
            role=payload.get("role", "user"),
            content=payload.get("content", ""),
            metadata=payload.get("metadata") or {},
        )
        harness.conversation_store.add(conversation_id, msg)
        return {"status": "ok"}

    # Steering endpoint replaced by create_human_steering_router() (M67).
    # The router provides intent classification, Chinese explanations,
    # M66 pause integration, and safety guardrails.

    @app.get("/runs/{run_id}/timeline")
    def run_timeline(run_id: str) -> list[dict]:
        events = harness.trace(run_id)
        return [e.__dict__ for e in events]

    @app.post("/checkpoints")
    def create_checkpoint(payload: dict) -> dict:
        workspace = checkpoint_workspace(payload, harness.runs, harness.workspace)
        service = CheckpointService(workspace) if workspace != harness.workspace else checkpoint_service
        checkpoint = service.create(
            run_id=str(payload.get("run_id", "")),
            goal_id=str(payload.get("goal_id", "")),
            changed_files=string_list(payload.get("changed_files")),
            constraints=string_list(payload.get("constraints")),
            pending_permissions=string_list(payload.get("pending_permissions")),
            evidence_refs=string_list(payload.get("evidence_refs")),
        )
        checkpoint_workspaces[checkpoint.id] = workspace
        return checkpoint.to_dict()

    @app.get("/checkpoints/{checkpoint_id}")
    def load_checkpoint(checkpoint_id: str, workspace: str | None = Query(default=None)) -> dict | None:
        target = workspace or checkpoint_workspaces.get(checkpoint_id, harness.workspace)
        service = CheckpointService(target) if target != harness.workspace else checkpoint_service
        checkpoint = service.load(checkpoint_id)
        return None if checkpoint is None else checkpoint.to_dict()

    @app.post("/review/evaluate")
    def evaluate_review(payload: dict) -> dict:
        checklist = ReviewChecklist(items=string_list(payload.get("items")))
        results = payload.get("results")
        result = review_gate.evaluate(checklist, results if isinstance(results, dict) else {})
        return {"passed": result.passed, "failures": result.failures}

    return app

app = create_app()
