from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class ToolRequest:
    id: str
    tool: str
    operation: str
    payload: dict

    @classmethod
    def create(cls, tool: str, operation: str, payload: dict) -> "ToolRequest":
        return cls(id=f"tool_{uuid4().hex[:12]}", tool=tool, operation=operation, payload=payload)


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    status: str
    reason: str
    output: str | None = None
    error: str | None = None

    @classmethod
    def denied(cls, request_id: str, reason: str) -> "ToolResult":
        return cls(request_id=request_id, status="denied", reason=reason)

    @classmethod
    def pending(cls, request_id: str, reason: str) -> "ToolResult":
        return cls(request_id=request_id, status="pending_permission", reason=reason)

    @classmethod
    def approved(cls, request_id: str, reason: str) -> "ToolResult":
        return cls(request_id=request_id, status="approved", reason=reason)

    @classmethod
    def rejected(cls, request_id: str, reason: str) -> "ToolResult":
        return cls(request_id=request_id, status="rejected", reason=reason)

    @classmethod
    def executed(cls, request_id: str, output: str) -> "ToolResult":
        return cls(request_id=request_id, status="executed", reason="execution completed", output=output)

    @classmethod
    def failed(cls, request_id: str, error: str) -> "ToolResult":
        return cls(request_id=request_id, status="failed", reason="execution failed", error=error)
