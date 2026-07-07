"""Execution audit integrity API. Read-only diagnostics only."""
from fastapi import APIRouter

from bolt_core.execution_audit_integrity import ExecutionAuditIntegrityService


def create_execution_audit_integrity_router(integrity: ExecutionAuditIntegrityService) -> APIRouter:
    router = APIRouter(tags=["execution-audit"])

    @router.get("/execution-audit/integrity")
    def execution_audit_integrity() -> list[dict]:
        return integrity.list_integrity()

    return router
