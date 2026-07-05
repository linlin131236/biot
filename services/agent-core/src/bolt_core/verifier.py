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
        if result.status == "executed":
            return VerificationResult("complete", result.status)
        if result.status == "pending_permission":
            return VerificationResult("pause_for_permission", result.status)
        if result.status in ("denied", "rejected"):
            return VerificationResult("terminal_failure", result.status)
        if result.status == "failed":
            return VerificationResult("recoverable_failure", result.status)
        return VerificationResult("needs_replan", result.status)
