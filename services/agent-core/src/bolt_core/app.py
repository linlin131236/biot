import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from bolt_core.model_settings import ModelSettingsConflictError
from bolt_core.checkpoint import CheckpointService
from bolt_core.persistence.artifact_store import ArtifactStore
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_handoff_api import create_execution_handoff_router
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.execution_queue_api import create_execution_queue_router
from bolt_core.execution_result_ingestion import ExecutionResultIngestionService
from bolt_core.app_helpers import goal_exists, permission_bridge_target
from bolt_core.harness import Harness
from bolt_core.harness_api import create_harness_router
from bolt_core.local_api_auth import install_local_api_auth
from bolt_core.review_gate import ReviewGate
from bolt_core.task_closure_api import create_task_closure_router
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_result_api import tool_result_dict
from bolt_core.workspace_lock import resolve_app_workspace

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
from bolt_core.tool_registry_api import create_tool_registry_router
from bolt_core.tool_manifest_api import create_tool_manifest_router
from bolt_core.tool_permission_contract_api import create_tool_permission_contract_router
from bolt_core.readonly_tool_runner_api import create_readonly_tool_runner_router
from bolt_core.write_tool_proposal_api import create_write_tool_proposal_router
from bolt_core.patch_proposal_api import create_patch_proposal_router
from bolt_core.approval_apply_api import create_approval_apply_router
from bolt_core.test_runner_integration_api import create_test_runner_integration_router
from bolt_core.tool_ecosystem_dogfood_api import create_tool_ecosystem_dogfood_router
from bolt_core.tool_call_eval_api import create_tool_call_eval_router
from bolt_core.patch_apply_eval_api import create_patch_apply_eval_router
from bolt_core.test_failure_diagnosis_eval_api import create_failure_diagnosis_eval_router
from bolt_core.permission_boundary_eval_api import create_permission_boundary_eval_router
from bolt_core.multi_agent_collaboration_eval_api import create_multi_agent_collaboration_eval_router
from bolt_core.memory_retrieval_eval_api import create_memory_retrieval_eval_router
from bolt_core.chinese_interaction_eval_api import create_chinese_interaction_eval_router
from bolt_core.e2e_task_dogfood_api import create_e2e_task_dogfood_router
from bolt_core.failure_recovery_dogfood_api import create_failure_recovery_dogfood_router
from bolt_core.agent_intelligence_dogfood_api import create_agent_intelligence_dogfood_router
from bolt_core.crash_recovery_api import create_crash_recovery_router
from bolt_core.data_migration_api import create_data_migration_router
from bolt_core.update_rollback_api import create_update_rollback_router
from bolt_core.privacy_security_audit_api import create_privacy_security_audit_router
from bolt_core.public_beta_readiness_api import create_public_beta_readiness_router
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
from bolt_core.role_protocol_api import create_role_protocol_router
from bolt_core.multi_agent_workflow_api import create_multi_agent_workflow_router
from bolt_core.researcher_integration_api import create_researcher_integration_router
from bolt_core.builder_api import create_builder_router
from bolt_core.reviewer_api import create_reviewer_router
from bolt_core.orchestrator_api import create_orchestrator_router
from bolt_core.sleep_wake_api import create_sleep_wake_router
from bolt_core.gate_freeze_api import create_gate_freeze_router
from bolt_core.gate_freeze_service import GateFrozenError, get_global_gate_freeze_service
from bolt_core.tool_verification_api import create_tool_verification_router
from bolt_core.auto_fix_api import create_auto_fix_router
from bolt_core.auto_continue_api import create_auto_continue_router
from bolt_core.autonomous_loop_api import create_autonomous_loop_router
from bolt_core.subtask_assignment_api import create_subtask_assignment_router
from bolt_core.reviewer_independent_gate_api import create_reviewer_independent_gate_router
from bolt_core.conflict_resolution_api import create_conflict_resolution_router
from bolt_core.skilllearner_review_loop_api import create_skilllearner_review_loop_router
from bolt_core.multi_agent_recovery_api import create_multi_agent_recovery_router
from bolt_core.team_dogfood import create_team_dogfood_router
from bolt_core.task_home_api import create_task_home_router
from bolt_core.permission_center_api import create_permission_center_router
from bolt_core.audit_timeline_api import create_audit_timeline_router
from bolt_core.diagnostics_center_api import create_diagnostics_center_router
from bolt_core.multi_task_queue_api import create_multi_task_queue_router
from bolt_core.failure_explanation_api import create_failure_explanation_router
from bolt_core.session_recovery_api import create_session_recovery_router
from bolt_core.settings_tools_api import create_settings_tools_router
from bolt_core.desktop_settings_api import create_desktop_settings_router
from bolt_core.workspace_api import create_workspace_router
from bolt_core.desktop_beta_dogfood_api import create_desktop_beta_dogfood_router
from bolt_core.product_workbench_api import create_product_workbench_router
from bolt_core.product_workbench_dogfood_api import create_product_workbench_dogfood_router
from bolt_core.desktop_beta_ship_api import create_desktop_beta_ship_router
from bolt_core.release_readiness import ReleaseReadinessService
from bolt_core.release_readiness_api import create_release_readiness_router
from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository
from bolt_core.persistence.recovery import RecoveryScanner
from bolt_core.app_routes import register as register_simple_routes
def create_app(
    execution_audit_path: str | Path | None = None,
    project_dir: str | Path | None = None,
    persistence_root: str | Path | None = None,
    local_api_token: str | None = None,
    require_local_api_token: bool = False,
    lock_default_workspace: bool = False,
    desktop_production: bool = False,
    credential_lifecycle=None, credential_configs=None,
    model_gateway=None, locked_workspace_binding=None, credential_store=None,
) -> FastAPI:
    app = FastAPI(title="Bolt Agent Core", docs_url="/docs" if not desktop_production else None, redoc_url="/redoc" if not desktop_production else None, openapi_url="/openapi.json" if not desktop_production else None)
    persistence = (
        ControlPlaneRepository(Database.open(Path(persistence_root)))
        if persistence_root is not None
        else None
    )
    app.state.persistence = persistence
    install_local_api_auth(app, local_api_token or os.environ.get("BOLT_AGENT_CORE_TOKEN"), require_token=require_local_api_token)
    workspace_root, locked_workspace = resolve_app_workspace(project_dir, os.environ.get("BOLT_WORKSPACE"), lock_default_workspace)
    audit_path = (
        resolve_execution_audit_path(execution_audit_path, workspace_root)
        if persistence is None
        else Path(persistence.database.path).with_name("__legacy_execution_audit_disabled__.json")
    )
    audit_store = ExecutionAuditStore(audit_path)
    audit_store_status = "ok"
    audit_store_error = ""
    closure_workspace_id = (
        persistence.save_workspace(str(workspace_root)) if persistence is not None else None
    )
    if persistence is not None:
        RecoveryScanner(persistence).recover_workspace(closure_workspace_id)
        persistence.reconcile_runtime_sessions(closure_workspace_id)
    try:
        if persistence is not None:
            # Single source of truth: closures persist through the repository's
            # dedicated task_closures table, never the legacy execution-audit JSON.
            task_closure_service = TaskClosureService(
                repository=persistence, workspace_id=closure_workspace_id
            )
            execution_queue_service = ExecutionQueueService(
                repository=persistence, workspace_id=closure_workspace_id
            )
            execution_handoff_service = ExecutionHandoffService(
                repository=persistence, workspace_id=closure_workspace_id
            )
        else:
            task_closure_service = TaskClosureService(audit_store)
            execution_queue_service = ExecutionQueueService(audit_store)
            execution_handoff_service = ExecutionHandoffService(audit_store)
    except ExecutionAuditStoreError as exc:
        audit_store_status = "degraded"
        audit_store_error = str(exc)
        task_closure_service = (
            TaskClosureService(repository=persistence, workspace_id=closure_workspace_id)
            if persistence is not None
            else TaskClosureService(None)
        )
        execution_queue_service = ExecutionQueueService(None)
        execution_handoff_service = ExecutionHandoffService(None)
    harness = Harness(workspace=str(workspace_root), task_closure_service=task_closure_service, locked_workspace=locked_workspace, locked_workspace_binding=locked_workspace_binding, model_gateway=model_gateway, persistence=persistence, credential_store=credential_store)
    app.state.harness = harness
    app.state.execution_queue_service = execution_queue_service
    app.state.execution_handoff_service = execution_handoff_service
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
    checkpoint_service = (
        CheckpointService(
            harness.workspace,
            repository=persistence,
            workspace_id=closure_workspace_id,
            artifact_store=ArtifactStore(persistence.database.path.parent.parent),
        )
        if persistence is not None else CheckpointService(harness.workspace)
    )
    app.state.checkpoint_service = checkpoint_service
    checkpoint_factory = (
        (lambda target: CheckpointService(
            target,
            repository=persistence,
            workspace_id=persistence.save_workspace(target),
            artifact_store=ArtifactStore(persistence.database.path.parent.parent),
        ))
        if persistence is not None else None
    )
    checkpoint_workspaces: dict[str, str] = {}
    review_gate = ReviewGate()
    gate_freeze_service = get_global_gate_freeze_service()
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
    app.include_router(create_tool_registry_router())
    app.include_router(create_tool_manifest_router())
    app.include_router(create_tool_permission_contract_router())
    app.include_router(create_readonly_tool_runner_router())
    app.include_router(create_write_tool_proposal_router())
    app.include_router(create_patch_proposal_router())
    app.include_router(create_approval_apply_router(project_dir=str(project_dir or Path.cwd()), gate_service=gate_freeze_service))
    app.include_router(create_test_runner_integration_router())
    app.include_router(create_tool_ecosystem_dogfood_router())
    app.include_router(create_tool_call_eval_router())
    app.include_router(create_patch_apply_eval_router())
    app.include_router(create_failure_diagnosis_eval_router())
    app.include_router(create_permission_boundary_eval_router())
    app.include_router(create_multi_agent_collaboration_eval_router())
    app.include_router(create_memory_retrieval_eval_router())
    app.include_router(create_chinese_interaction_eval_router())
    app.include_router(create_e2e_task_dogfood_router())
    app.include_router(create_failure_recovery_dogfood_router())
    app.include_router(create_agent_intelligence_dogfood_router())
    app.include_router(create_crash_recovery_router(str(project_dir or Path.cwd())))
    app.include_router(create_data_migration_router(str(project_dir or Path.cwd())))
    app.include_router(create_update_rollback_router(str(project_dir or Path.cwd())))
    app.include_router(create_privacy_security_audit_router(str(project_dir or Path.cwd())))
    app.include_router(create_public_beta_readiness_router(str(project_dir or Path.cwd())))
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
    app.include_router(create_role_protocol_router())
    app.include_router(create_multi_agent_workflow_router())
    app.include_router(create_researcher_integration_router())
    app.include_router(create_builder_router())
    app.include_router(create_reviewer_router())
    app.include_router(create_orchestrator_router())
    app.include_router(create_sleep_wake_router())
    app.include_router(create_gate_freeze_router(gate_freeze_service))
    app.include_router(create_tool_verification_router())
    app.include_router(create_auto_fix_router())
    app.include_router(create_auto_continue_router(gate_service=gate_freeze_service))
    app.include_router(create_autonomous_loop_router(gate_service=gate_freeze_service))
    app.include_router(create_subtask_assignment_router())
    app.include_router(create_reviewer_independent_gate_router())
    app.include_router(create_conflict_resolution_router())
    app.include_router(create_skilllearner_review_loop_router())
    app.include_router(create_multi_agent_recovery_router())
    app.include_router(create_team_dogfood_router())
    app.include_router(create_task_home_router(harness, diagnostics_service, planner_service))
    app.include_router(create_permission_center_router(harness.permissions))
    app.include_router(create_audit_timeline_router(timeline_service, task_closure_service))
    app.include_router(create_diagnostics_center_router(diagnostics_service, integrity_service))
    app.include_router(create_multi_task_queue_router(harness, task_closure_service, planner_service))
    app.include_router(create_failure_explanation_router())
    app.include_router(create_session_recovery_router())
    app.include_router(create_settings_tools_router())
    app.include_router(create_desktop_settings_router(
        str(project_dir or Path.cwd()),
        credential_lifecycle=credential_lifecycle,
        credential_configs=credential_configs,
    ))
    app.include_router(create_workspace_router(
        str(project_dir or Path.cwd()), persistence=persistence,
        workspace_id=closure_workspace_id,
    ))
    app.include_router(create_desktop_beta_dogfood_router())
    app.include_router(create_product_workbench_router(str(project_dir or Path.cwd())))
    app.include_router(create_product_workbench_dogfood_router(str(project_dir or Path.cwd())))
    app.include_router(create_desktop_beta_ship_router(str(project_dir or Path.cwd())))
    app.include_router(create_harness_router(harness))

    @app.get("/health")
    def health() -> dict[str, str]:
        if audit_store_status != "ok":
            return {
                "status": "degraded",
                "service": "bolt-agent-core",
                "audit_store": audit_store_status,
                "audit_error": audit_store_error,
            }
        return {"status": "ok", "service": "bolt-agent-core"}

    @app.get("/context/p0")
    def p0_context() -> dict[str, list]: return harness.p0_context()

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
        try:
            return harness.update_model_settings(payload).__dict__
        except ModelSettingsConflictError as error:
            raise HTTPException(status_code=409, detail="model settings revision conflict") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.delete("/model/settings")
    def delete_model_settings(revision: int) -> dict:
        harness.model_settings.delete(revision=revision)
        return harness.model_settings_status().__dict__

    @app.get("/permissions/pending")
    def pending_permissions() -> list[dict]:
        return [item.__dict__ for item in harness.pending_permissions()]

    @app.post("/permissions/{request_id}/approve")
    def approve_permission(request_id: str) -> dict[str, str | None]:
        try:
            gate_freeze_service.assert_not_frozen()
        except GateFrozenError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=423, detail=f"Gate 已冻结：{exc}") from exc
        result = harness.approve_permission(request_id)
        result_ingestion.ingest(result)
        return tool_result_dict(result)

    @app.post("/permissions/{request_id}/reject")
    def reject_permission(request_id: str) -> dict[str, str | None]:
        result = harness.reject_permission(request_id)
        result_ingestion.ingest(result)
        return tool_result_dict(result)

    register_simple_routes(
        app, harness, result_ingestion, checkpoint_service, checkpoint_workspaces,
        review_gate, checkpoint_factory,
    )

    return app


@asynccontextmanager
async def fail_without_local_token(_app: FastAPI):
    raise RuntimeError("本地 API 鉴权令牌未配置，拒绝以裸奔模式启动。请通过 BOLT_AGENT_CORE_TOKEN 环境变量提供。")
    yield


_module_token = os.environ.get("BOLT_AGENT_CORE_TOKEN")
app = create_app(local_api_token=_module_token, require_local_api_token=True, lock_default_workspace=True) if _module_token else FastAPI(title="Bolt Agent Core", lifespan=fail_without_local_token)
