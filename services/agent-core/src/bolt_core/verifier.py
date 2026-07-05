from dataclasses import dataclass

from bolt_core.tool_protocol import ToolResult


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str


class Verifier:
    def verify(self, result: ToolResult | None) -> VerificationResult:
        if result is None:
            return VerificationResult("needs_replan", "no tool result")
        if result.status in ("executed", "pending_permission", "denied", "failed"):
            return VerificationResult("passed", result.status)
        return VerificationResult("needs_replan", result.status)
