"""Execution audit diagnostics API. Read-only diagnostics only."""
from fastapi import APIRouter, Query

from bolt_core.execution_audit_diagnostics import ExecutionAuditDiagnosticsService


def create_execution_audit_diagnostics_router(diagnostics: ExecutionAuditDiagnosticsService) -> APIRouter:
    router = APIRouter(tags=["execution-audit"])

    @router.get("/execution-audit/diagnostics")
    def execution_audit_diagnostics(closure_id: str | None = Query(default=None)) -> list[dict]:
        return diagnostics.list_diagnostics(closure_id)

    return router
