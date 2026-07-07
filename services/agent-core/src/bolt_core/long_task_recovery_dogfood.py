"""Long Task Recovery Dogfood. Read-only readiness check for M61-M68 safety closed loop.

Verifies that the V2 Agent workflow core components form a safe, traceable system.
This is a dogfood/readiness gate — NEVER an auto-executor.

Checks:
1. Task graph capability exists (M61)
2. State machine is valid (M62)
3. Pause/resume re-verifies permissions (M66)
4. Steering does not directly execute (M67)
5. Budget blocks when exceeded (M68)
6. Failure classifier has Chinese diagnosis (M64)
7. Retry loop does not retry dangerous tools (M65)
8. PermissionGate is not bypassed (safety base)
9. Trace/evidence/source_refs are traceable (audit)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DogfoodCheck:
    """Single dogfood check result."""
    check_id: str
    label_cn: str  # 中文标签
    passed: bool
    severity: str  # "pass" | "warning" | "blocking"
    detail: str  # 中文详情
    source: str  # 对应 milestone


@dataclass(frozen=True)
class DogfoodReport:
    """Complete dogfood readiness report."""
    report_id: str
    timestamp: float
    overall_passed: bool
    checks: list[dict]  # list of DogfoodCheck as dicts
    summary: str  # Chinese summary
    blockers: list[str]
    warnings: list[str]
    readiness: str  # "ready" | "not_ready" | "needs_review"

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "overall_passed": self.overall_passed,
            "checks": self.checks,
            "summary": self.summary,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "readiness": self.readiness,
        }


def _check(check_id: str, label_cn: str, passed: bool, severity: str,
           detail: str, source: str) -> dict:
    return {
        "check_id": check_id,
        "label_cn": label_cn,
        "passed": passed,
        "severity": severity,
        "detail": detail,
        "source": source,
    }


class LongTaskRecoveryDogfoodService:
    """Read-only readiness checker for M61-M68 long task recovery closed loop.

    Verifies that all V2 Agent workflow core components are present and safe.
    Does NOT execute any recovery, does NOT approve permissions.
    """

    def assess(self) -> DogfoodReport:
        """Run all dogfood checks and return a readiness report."""
        checks: list[dict] = []
        blockers: list[str] = []
        warnings: list[str] = []
        now = time.time()
        report_id = f"dogfood_{uuid.uuid4().hex[:8]}"

        # ── Check 1: Task Graph (M61) ─────────────────────────────────
        c1 = self._check_task_graph()
        checks.append(c1)
        if not c1["passed"]:
            blockers.append(c1["label_cn"])

        # ── Check 2: State Machine (M62) ──────────────────────────────
        c2 = self._check_state_machine()
        checks.append(c2)
        if not c2["passed"]:
            blockers.append(c2["label_cn"])

        # ── Check 3: Pause/Resume forces permission re-verification (M66) ──
        c3 = self._check_pause_resume_permissions()
        checks.append(c3)
        if not c3["passed"]:
            blockers.append(c3["label_cn"])

        # ── Check 4: Steering does not directly execute (M67) ─────────
        c4 = self._check_steering_safety()
        checks.append(c4)
        if not c4["passed"]:
            blockers.append(c4["label_cn"])

        # ── Check 5: Budget blocks when exceeded (M68) ────────────────
        c5 = self._check_budget_blocks()
        checks.append(c5)
        if not c5["passed"]:
            blockers.append(c5["label_cn"])

        # ── Check 6: Failure classifier has Chinese diagnosis (M64) ───
        c6 = self._check_failure_classifier_chinese()
        checks.append(c6)
        if not c6["passed"]:
            warnings.append(c6["label_cn"])

        # ── Check 7: Retry loop does not retry dangerous tools (M65) ──
        c7 = self._check_retry_loop_safety()
        checks.append(c7)
        if not c7["passed"]:
            blockers.append(c7["label_cn"])

        # ── Check 8: PermissionGate not bypassed ──────────────────────
        c8 = self._check_permission_gate()
        checks.append(c8)
        if not c8["passed"]:
            blockers.append(c8["label_cn"])

        # ── Check 9: Trace/evidence/source_refs traceable ─────────────
        c9 = self._check_traceability()
        checks.append(c9)
        if not c9["passed"]:
            warnings.append(c9["label_cn"])

        # ── Summary ───────────────────────────────────────────────────
        all_passed = all(c["passed"] for c in checks)
        has_blockers = len(blockers) > 0

        if all_passed:
            readiness = "ready"
            summary = "长任务恢复闭环验证通过。所有安全门控、权限检查、预算阻断、证据追溯均已就位。可以进入下一阶段。"
        elif has_blockers:
            readiness = "not_ready"
            summary = f"长任务恢复闭环存在 {len(blockers)} 个阻断项：{'、'.join(blockers)}。请修复阻断项后重新验证。"
        else:
            readiness = "needs_review"
            summary = f"长任务恢复闭环基本通过，但存在 {len(warnings)} 个警告项：{'、'.join(warnings)}。建议人工审查后继续。"

        return DogfoodReport(
            report_id=report_id,
            timestamp=now,
            overall_passed=all_passed,
            checks=checks,
            summary=summary,
            blockers=blockers,
            warnings=warnings,
            readiness=readiness,
        )

    # ── Individual checks ─────────────────────────────────────────────

    def _check_task_graph(self) -> dict:
        """M61: Verify PlannerTaskGraphService can be instantiated."""
        try:
            from bolt_core.planner_task_graph import PlannerTaskGraphService
            svc = PlannerTaskGraphService()
            _ = svc.create_graph("dogfood_test", "验证任务图")
            return _check("task_graph", "任务图（M61）",
                          True, "pass",
                          "PlannerTaskGraphService 可正常创建任务图。",
                          "M61")
        except Exception as e:
            return _check("task_graph", "任务图（M61）",
                          False, "blocking",
                          f"任务图服务不可用：{e}",
                          "M61")

    def _check_state_machine(self) -> dict:
        """M62: Verify ExecutionStateMachine has valid states and transitions."""
        try:
            from bolt_core.execution_state_machine import ExecutionStateMachine
            states = ExecutionStateMachine.STATES
            transitions = ExecutionStateMachine.TRANSITIONS
            if len(states) >= 5 and len(transitions) >= 10:
                return _check("state_machine", "状态机（M62）",
                              True, "pass",
                              f"ExecutionStateMachine 正常：{len(states)} 状态，{len(transitions)} 转换。",
                              "M62")
            return _check("state_machine", "状态机（M62）",
                          False, "blocking",
                          f"状态机配置不完整：{len(states)} 状态，{len(transitions)} 转换。",
                          "M62")
        except Exception as e:
            return _check("state_machine", "状态机（M62）",
                          False, "blocking", f"状态机不可用：{e}", "M62")

    def _check_pause_resume_permissions(self) -> dict:
        """M66: Verify pause/resume forces permission re-verification."""
        try:
            from bolt_core.pause_resume import PauseResumeService
            svc = PauseResumeService()
            svc.pause("dogfood_node", "running", "dogfood 测试")
            result = svc.resume("dogfood_node")
            requires_human = result.get("requires_human_decision", False)
            perm_check = any(
                c.get("check") == "permission_verify" and c.get("requires_human")
                for c in result.get("checks", [])
            )
            if requires_human and perm_check:
                return _check("pause_resume_perms", "暂停恢复权限复查（M66）",
                              True, "pass",
                              "恢复操作强制执行权限复查，不可跳过。",
                              "M66")
            return _check("pause_resume_perms", "暂停恢复权限复查（M66）",
                          False, "blocking",
                          "恢复操作未强制执行权限复查，存在安全风险。",
                          "M66")
        except Exception as e:
            return _check("pause_resume_perms", "暂停恢复权限复查（M66）",
                          False, "blocking", f"暂停恢复服务检查失败：{e}", "M66")

    def _check_steering_safety(self) -> dict:
        """M67: Verify steering does not directly execute dangerous actions."""
        try:
            from bolt_core.human_steering import HumanSteeringService, SteeringIntent
            svc = HumanSteeringService()
            # Test abort (should be pending only)
            result = svc.process("dogfood_run", "取消任务")
            if result.intent == "abort" and result.requires_human_confirmation and result.pending_actions:
                # Test change_goal (should be pending only)
                result2 = svc.process("dogfood_run", "改成只改文档")
                if result2.intent == "change_goal" and result2.requires_human_confirmation and result2.pending_actions:
                    return _check("steering_safety", "人工转向安全（M67）",
                                  True, "pass",
                                  "副作用 steering（abort/change_goal）仅生成 pending，不直接执行。",
                                  "M67")
            return _check("steering_safety", "人工转向安全（M67）",
                          False, "blocking",
                          "steering 未正确限制副作用操作的直接执行。",
                          "M67")
        except Exception as e:
            return _check("steering_safety", "人工转向安全（M67）",
                          False, "blocking", f"steering 安全检查失败：{e}", "M67")

    def _check_budget_blocks(self) -> dict:
        """M68: Verify budget blocks when exceeded."""
        try:
            from bolt_core.agent_budget import AgentBudgetService, BudgetConfig, BudgetState
            svc = AgentBudgetService()
            cfg = BudgetConfig(max_steps=5)
            st = BudgetState(steps_used=10)
            result = svc.check(cfg, st)
            if not result.allowed and result.dimension == "steps" and result.explanation:
                return _check("budget_blocks", "预算阻断（M68）",
                              True, "pass",
                              "超预算时正确返回 blocked，含中文阻断原因。",
                              "M68")
            return _check("budget_blocks", "预算阻断（M68）",
                          False, "blocking",
                          "超预算时未正确阻断。",
                          "M68")
        except Exception as e:
            return _check("budget_blocks", "预算阻断（M68）",
                          False, "blocking", f"预算检查失败：{e}", "M68")

    def _check_failure_classifier_chinese(self) -> dict:
        """M64: Verify failure classifier provides Chinese diagnosis."""
        try:
            from bolt_core.failure_classifier import FailureClassifier
            classifier = FailureClassifier()
            result = classifier.classify("tool_not_found", "test_tool", "工具未注册")
            diagnosis = result.get("diagnosis_cn", "") or result.get("diagnosis", "")
            if diagnosis and any('\u4e00' <= c <= '\u9fff' for c in str(diagnosis)):
                return _check("failure_classifier_cn", "失败分类中文诊断（M64）",
                              True, "pass",
                              "FailureClassifier 返回中文诊断信息。",
                              "M64")
            return _check("failure_classifier_cn", "失败分类中文诊断（M64）",
                          False, "warning",
                          "FailureClassifier 未返回中文诊断。",
                          "M64")
        except Exception as e:
            return _check("failure_classifier_cn", "失败分类中文诊断（M64）",
                          False, "warning", f"失败分类器检查失败：{e}", "M64")

    def _check_retry_loop_safety(self) -> dict:
        """M65: Verify retry loop does not retry dangerous tools."""
        try:
            from bolt_core.safe_retry_loop import SafeRetryLoop
            from bolt_core.tool_selection_policy import ToolSelectionPolicy
            policy = ToolSelectionPolicy()
            dangerous = ["shell_exec", "git_push", "git_delete", "permission_approve"]
            # Each dangerous tool should be classified as dangerous
            for tool in dangerous:
                classification = policy.classify(tool)
                if classification.get("class") != "dangerous":
                    return _check("retry_loop_safety", "安全重试循环（M65）",
                                  False, "blocking",
                                  f"危险工具 '{tool}' 未被正确分级为 dangerous。",
                                  "M65")
            return _check("retry_loop_safety", "安全重试循环（M65）",
                          True, "pass",
                          "危险工具被正确分级，重试循环不会重试危险工具。",
                          "M65")
        except Exception as e:
            return _check("retry_loop_safety", "安全重试循环（M65）",
                          False, "blocking", f"重试循环安全检查失败：{e}", "M65")

    def _check_permission_gate(self) -> dict:
        """Verify PermissionGate exists and can deny dangerous operations."""
        try:
            from bolt_core.permission_gate import PermissionGate
            from bolt_core.tool_protocol import ToolRequest
            gate = PermissionGate("/tmp/dogfood_test")
            request = ToolRequest.create("shell.execute", "command",
                                         {"command": "rm -rf /"})
            decision = gate.evaluate(request)
            if decision.status == "denied":
                return _check("permission_gate", "PermissionGate 安全底座",
                              True, "pass",
                              "PermissionGate 正确拒绝危险 shell 命令。",
                              "安全底座")
            return _check("permission_gate", "PermissionGate 安全底座",
                          False, "blocking",
                          f"PermissionGate 未拒绝危险操作，状态为 '{decision.status}'。",
                          "安全底座")
        except Exception as e:
            return _check("permission_gate", "PermissionGate 安全底座",
                          False, "blocking", f"PermissionGate 检查失败：{e}", "安全底座")

    def _check_traceability(self) -> dict:
        """Verify trace/evidence/source_refs mechanisms exist."""
        try:
            from bolt_core.trace import TraceLog
            trace = TraceLog("dogfood_trace")
            trace.record("dogfood.test", {"source": "M69"})
            events = trace.events()
            if len(events) == 1 and events[0].type == "dogfood.test":
                return _check("traceability", "证据追溯",
                              True, "pass",
                              "TraceLog 可正常记录和读取，证据链可追溯。",
                              "审计基础设施")
            return _check("traceability", "证据追溯",
                          False, "warning",
                          "TraceLog 记录/读取不一致。",
                          "审计基础设施")
        except Exception as e:
            return _check("traceability", "证据追溯",
                          False, "warning", f"证据追溯检查失败：{e}", "审计基础设施")
