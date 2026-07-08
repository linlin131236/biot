"""Permission Center Service (M92). Enriches pending permissions with
risk classification, Chinese explanations, and impact descriptions.

Read-only aggregation. Does NOT approve, reject, or modify permissions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from bolt_core.evidence_redactor import redact


# ── Risk classification ────────────────────────────────────────────────

_HIGH_RISK_TOOLS = {"shell_executor", "patch_engine", "file_writer", "git"}
_HIGH_RISK_OPS = {"execute", "write", "delete", "patch", "commit", "push"}
_MEDIUM_RISK_OPS = {"read", "create", "install", "update"}
_TOOL_CN: dict[str, str] = {
    "shell_executor": "命令行执行",
    "patch_engine": "代码补丁",
    "file_writer": "文件写入",
    "git": "版本控制",
    "web_search": "网络搜索",
    "web_fetch": "网页抓取",
    "file_reader": "文件读取",
}
_OP_CN: dict[str, str] = {
    "execute": "执行", "write": "写入", "delete": "删除",
    "patch": "打补丁", "commit": "提交", "push": "推送",
    "read": "读取", "create": "创建", "install": "安装",
    "update": "更新", "search": "搜索", "fetch": "抓取",
}

_RISK_EXPLANATIONS: dict[str, str] = {
    "high": "此操作可能修改文件系统或执行系统命令，需要谨慎审查。",
    "medium": "此操作可能读取敏感数据或访问外部资源。",
    "low": "此操作仅读取或查询信息，风险较低。",
}

_IMPACT_TEMPLATES: dict[str, str] = {
    "high": "批准后将对项目文件或系统环境产生实际变更，建议确认操作内容后再批准。",
    "medium": "批准后将访问指定资源或读取数据，不直接修改文件。",
    "low": "批准后仅执行信息查询操作，不会修改任何文件或系统状态。",
}


def _classify_risk(tool: str, operation: str) -> str:
    if tool in _HIGH_RISK_TOOLS:
        return "high"
    if operation in _HIGH_RISK_OPS:
        return "high"
    if operation in _MEDIUM_RISK_OPS:
        return "medium"
    return "low"


def _risk_label(risk: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(risk, risk)


# ── Data model ──────────────────────────────────────────────────────────

@dataclass
class PermissionCenterItem:
    id: str
    request_id: str
    run_id: str
    tool: str
    tool_cn: str
    operation: str
    operation_cn: str
    payload_summary: str
    reason: str
    status: str
    status_cn: str
    risk_level: str
    risk_label_cn: str
    risk_explanation_cn: str
    impact_cn: str
    action_cn: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "tool": self.tool,
            "tool_cn": self.tool_cn,
            "operation": self.operation,
            "operation_cn": self.operation_cn,
            "payload_summary": self.payload_summary,
            "reason": self.reason,
            "status": self.status,
            "status_cn": self.status_cn,
            "risk_level": self.risk_level,
            "risk_label_cn": self.risk_label_cn,
            "risk_explanation_cn": self.risk_explanation_cn,
            "impact_cn": self.impact_cn,
            "action_cn": self.action_cn,
        }


@dataclass
class PermissionCenterSummary:
    items: list[PermissionCenterItem] = field(default_factory=list)
    total_pending: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "total_pending": self.total_pending,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "updated_at": self.updated_at,
        }


_STATUS_CN: dict[str, str] = {
    "pending_permission": "等待批准",
    "approved": "已批准",
    "rejected": "已拒绝",
    "denied": "已拒绝",
}

_ACTION_CN: dict[str, str] = {
    "pending_permission": "请前往权限审批面板处理此请求。",
    "approved": "此权限已批准，操作已执行。",
    "rejected": "此权限已拒绝，操作未执行。",
    "denied": "此权限已被拒绝。",
}


# ── Service ─────────────────────────────────────────────────────────────

class PermissionCenterService:
    """Read-only aggregation of permission data with Chinese explanations."""

    def __init__(self, permission_queue):
        self._queue = permission_queue

    def get_summary(self) -> PermissionCenterSummary:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            pending = self._queue.pending()
        except Exception:
            pending = []

        items: list[PermissionCenterItem] = []
        high = medium = low = 0

        for p in pending:
            risk = _classify_risk(p.tool, p.operation)
            if risk == "high":
                high += 1
            elif risk == "medium":
                medium += 1
            else:
                low += 1

            payload_str = redact(str(p.payload))[:200] if p.payload else "无附加数据"
            tool_cn = _TOOL_CN.get(p.tool, p.tool)
            op_cn = _OP_CN.get(p.operation, p.operation)

            items.append(PermissionCenterItem(
                id=p.id,
                request_id=getattr(p, "request_id", p.id),
                run_id=p.run_id,
                tool=p.tool,
                tool_cn=tool_cn,
                operation=p.operation,
                operation_cn=op_cn,
                payload_summary=payload_str,
                reason=p.reason or "未提供原因",
                status=p.status,
                status_cn=_STATUS_CN.get(p.status, p.status),
                risk_level=risk,
                risk_label_cn=_risk_label(risk),
                risk_explanation_cn=_RISK_EXPLANATIONS.get(risk, ""),
                impact_cn=_IMPACT_TEMPLATES.get(risk, ""),
                action_cn=_ACTION_CN.get(p.status, "请查看详情。"),
            ))

        # Sort: high risk first, then by tool
        items.sort(key=lambda i: (0 if i.risk_level == "high" else 1 if i.risk_level == "medium" else 2, i.tool))

        return PermissionCenterSummary(
            items=items,
            total_pending=len(pending),
            high_risk_count=high,
            medium_risk_count=medium,
            low_risk_count=low,
            updated_at=now,
        )
