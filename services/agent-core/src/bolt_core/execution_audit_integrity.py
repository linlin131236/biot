"""Read-only execution audit integrity guard. Never fixes or executes."""
from __future__ import annotations

import json
import uuid

from bolt_core.execution_audit_store import ExecutionAuditStore, ExecutionAuditStoreError


class ExecutionAuditIntegrityService:
    def __init__(self, store: ExecutionAuditStore) -> None:
        self._store = store

    def list_integrity(self) -> list[dict]:
        diagnostics: list[dict] = []
        if not self._store._path.exists():
            return diagnostics

        data: dict | None = None
        damaged = False
        try:
            raw = self._store._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            damaged = True
            diagnostics.append(_diagnostic(
                "json_damaged",
                "blocking",
                "审计文件 JSON 已损坏：无法解析",
                "请手动检查文件内容并修复或删除文件后重新生成",
            ))

        if damaged or not isinstance(data, dict):
            if not damaged:
                diagnostics.append(_diagnostic(
                    "root_not_object",
                    "blocking",
                    "审计文件根元素必须是 JSON 对象",
                    "请手动检查文件结构",
                ))
            return diagnostics

        for field, label_cn in [
            ("queue_items", "队列项"),
            ("handoff_records", "交接记录"),
            ("closure_records", "闭环证据"),
        ]:
            if field in data and not isinstance(data[field], list):
                diagnostics.append(_diagnostic(
                    f"{field}_not_list",
                    "blocking",
                    f"审计文件 {label_cn}（{field}）类型错误：期望列表，实际为 {type(data[field]).__name__}",
                    f"请手动修复 {field} 为 JSON 数组",
                ))

        if not diagnostics:
            diagnostics.append(_diagnostic(
                "clean",
                "info",
                "审计文件结构正常",
                "无需处理",
            ))

        return diagnostics


def _diagnostic(code: str, severity: str, summary: str, suggestion: str) -> dict:
    return {
        "id": f"integrity_{code}_{uuid.uuid4().hex[:8]}",
        "code": code,
        "severity": severity,
        "severity_label": _severity_label(severity),
        "summary": summary,
        "suggestion": suggestion,
    }


def _severity_label(severity: str) -> str:
    if severity == "blocking":
        return "阻断"
    if severity == "warning":
        return "警告"
    return "提示"
