"""Permission Boundary Eval (M114). Verify PermissionGate/Tool Permission Contract
correctly blocks dangerous, unauthorized, and bypass attempts.

Uses PermissionContractEngine with a standard tool registry to evaluate
boundary decisions. No real operations executed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS, CATEGORY_READ_ONLY, CATEGORY_SIDE_EFFECT, CATEGORY_WRITE,
    PERM_DANGEROUS, PERM_EXECUTE, PERM_READ, PERM_WRITE,
    RISK_CRITICAL, RISK_HIGH, RISK_LOW, RISK_MEDIUM,
    ToolDef, ToolRegistry,
)
from bolt_core.tool_permission_contract import (
    DECISION_ALLOWED, DECISION_DENIED, DECISION_NEEDS_APPROVAL,
    PermissionContractEngine, PermissionDecision,
)

_DA = DECISION_ALLOWED; _DD = DECISION_DENIED; _DN = DECISION_NEEDS_APPROVAL
_CRO = CATEGORY_READ_ONLY; _CSE = CATEGORY_SIDE_EFFECT
_CWR = CATEGORY_WRITE; _CDG = CATEGORY_DANGEROUS
_PRD = PERM_READ; _PWR = PERM_WRITE; _PEX = PERM_EXECUTE; _PDG = PERM_DANGEROUS


def _build_perm_eval_registry() -> ToolRegistry:
    r = ToolRegistry()
    for t in [
        ToolDef("read_file", "读取文件", _CRO, "读文件", permission_required=_PRD, risk_level=RISK_LOW),
        ToolDef("write_file", "写入文件", _CWR, "写文件", permission_required=_PWR, risk_level=RISK_MEDIUM),
        ToolDef("run_test", "运行测试", _CSE, "跑测试", permission_required=_PEX, risk_level=RISK_MEDIUM),
        ToolDef("push_code", "推送代码", _CDG, "push", permission_required=_PDG, risk_level=RISK_CRITICAL),
        ToolDef("create_release", "创建发布", _CDG, "release", permission_required=_PDG, risk_level=RISK_CRITICAL),
        ToolDef("create_tag", "创建标签", _CDG, "tag", permission_required=_PDG, risk_level=RISK_CRITICAL),
        ToolDef("delete_file", "删除文件", _CDG, "删除", permission_required=_PDG, risk_level=RISK_CRITICAL),
        ToolDef("read_secret", "读取密钥", _CDG, "读密钥", permission_required=_PDG, risk_level=RISK_CRITICAL),
    ]:
        r.register(t)
    return r


@dataclass(frozen=True)
class PermBoundaryEvalCase:
    case_id: str; description: str; tool_id: str; operation: str
    expected_decision: str  # allowed / denied / needs_approval
    chinese_reason: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "description": self.description,
                "tool_id": self.tool_id, "operation": self.operation,
                "expected_decision": self.expected_decision,
                "chinese_reason": self.chinese_reason}


@dataclass(frozen=True)
class PermBoundaryEvalResult:
    case_id: str; passed: bool; expected_decision: str; actual_decision: str
    chinese_reason: str; boundary: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "expected_decision": self.expected_decision,
                "actual_decision": self.actual_decision,
                "chinese_reason": self.chinese_reason, "boundary": self.boundary}


@dataclass
class PermBoundaryEvalSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[PermBoundaryEvalResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "权限边界评估仅验证 PermissionContractEngine 决策，不执行任何真实操作。"}


class PermissionBoundaryEvalService:
    """M114 权限边界评估服务。"""

    def __init__(self) -> None:
        self._registry = _build_perm_eval_registry()
        self._engine = PermissionContractEngine()

    def run_all(self) -> PermBoundaryEvalSummary:
        results = []
        for case in self._cases():
            decision = self._engine.evaluate(tool_id=case.tool_id, operation=case.operation,
                                             registry=self._registry)
            actual = decision.decision
            passed = actual == case.expected_decision
            boundary = ""
            if case.expected_decision == _DA:
                boundary = "允许"
            elif case.expected_decision == _DD:
                boundary = "阻断"
            elif case.expected_decision == _DN:
                boundary = "需批准"
            results.append(PermBoundaryEvalResult(
                case_id=case.case_id, passed=passed,
                expected_decision=case.expected_decision,
                actual_decision=actual, chinese_reason=decision.reason,
                boundary=boundary,
            ))
        p = sum(1 for r in results if r.passed)
        return PermBoundaryEvalSummary(total_cases=len(results), passed=p,
                                       failed=len(results) - p, results=results)

    @staticmethod
    def _cases() -> list[PermBoundaryEvalCase]:
        PC = PermBoundaryEvalCase
        return [
            PC("read_allowed", "只读工具允许执行", "read_file", "", _DA, "只读文件无需批准"),
            PC("write_needs_approval", "写入工具需要批准", "write_file", "", _DN, "写入需人工批准"),
            PC("execute_needs_approval", "执行工具需要批准", "run_test", "", _DN, "执行测试需批准"),
            PC("dangerous_always_blocked_push", "push永久危险", "push_code", "push", _DN, "push需用户批准"),
            PC("dangerous_always_blocked_release", "release永久危险", "create_release", "release", _DN, "release需批准"),
            PC("dangerous_always_blocked_tag", "tag永久危险", "create_tag", "tag", _DN, "tag需批准"),
            PC("dangerous_always_blocked_delete", "delete永久危险", "delete_file", "delete", _DN, "delete需批准"),
            PC("secret_read_blocked", "密钥读取阻断", "read_secret", "", _DN, "密钥读取需最高权限"),
            PC("unknown_tool_blocked", "未知工具阻断", "nonexistent_tool", "", _DD, "未知工具默认拒绝"),
            PC("read_no_human_approval", "只读无需人工批准", "read_file", "", _DA, ""),
            PC("dangerous_requires_human", "dangerous必须人工批准", "delete_file", "", _DN, ""),
            PC("write_requires_human", "写入必须人工批准", "write_file", "", _DN, ""),
        ]
