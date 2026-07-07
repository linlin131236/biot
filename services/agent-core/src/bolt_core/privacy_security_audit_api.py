"""M124 privacy and security audit API. Read-only."""
from fastapi import APIRouter

from bolt_core.privacy_security_audit import PrivacySecurityAuditService


def create_privacy_security_audit_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["reliability"])

    @router.get("/reliability/privacy-security-audit")
    def privacy_security_review() -> dict:
        result = PrivacySecurityAuditService(project_dir).review()
        return {
            "review": result.to_dict(),
            "disclaimer": "只读隐私安全审计，不会替代 PermissionGate，也不会自动批准任何权限。",
        }

    return router
