"""Evidence-based task verification. Builds plans and assessments only."""
from __future__ import annotations

from dataclasses import dataclass

from bolt_core.task_closure import TaskClosure, TaskClosureStatus, TaskTemplateId


@dataclass(frozen=True)
class VerificationCheck:
    id: str
    label: str
    command: str | None
    required: bool
    satisfied: bool
    evidence: str
    missing_reason: str


@dataclass(frozen=True)
class VerificationPlan:
    template_id: str
    checks: list[VerificationCheck]


@dataclass(frozen=True)
class VerificationAssessment:
    status: str
    summary: str
    missing: list[str]
    repair_suggestions: list[str]


def build_verification_plan(closure: TaskClosure) -> VerificationPlan:
    return VerificationPlan(str(closure.template_id), _checks_for(closure))


def assess_completion(closure: TaskClosure) -> VerificationAssessment:
    if closure.status == TaskClosureStatus.WAITING_PERMISSION:
        return VerificationAssessment("waiting_permission", "等待人工批准", [], ["等待人工批准后再继续验证"])
    if closure.status == TaskClosureStatus.STOPPED:
        return VerificationAssessment("stopped", "已达到最大步数", ["需要重新规划或人工处理"], ["重新规划任务或交给人工处理"])
    if closure.status == TaskClosureStatus.FAILED:
        return VerificationAssessment("needs_repair", "执行失败，需要修复", [], _repair_suggestions(closure))

    plan = build_verification_plan(closure)
    missing = [check.missing_reason for check in plan.checks if check.required and not check.satisfied]
    if missing:
        return VerificationAssessment("missing_evidence", "缺少验证证据", missing, _repair_suggestions(closure))
    return VerificationAssessment("passed", "验证证据已满足", [], [])


def verification_plan_dict(plan: VerificationPlan) -> dict:
    return {"template_id": plan.template_id, "checks": [check.__dict__ for check in plan.checks]}


def verification_assessment_dict(assessment: VerificationAssessment) -> dict:
    return assessment.__dict__


def _checks_for(closure: TaskClosure) -> list[VerificationCheck]:
    template_id = str(closure.template_id)
    if template_id == TaskTemplateId.DOCS:
        return [_change_check(closure, "文档变更证据", "docs"), _quality_check(closure, "文档检查证据", "pnpm lint:docs", ("docs", "lint"))]
    if template_id == TaskTemplateId.TEST:
        return [_test_change_check(closure), _quality_check(closure, "测试通过证据", "pytest 或 pnpm test", ("test", "pytest", "vitest"))]
    if template_id == TaskTemplateId.QUALITY:
        return [_quality_check(closure, "质量门证据", "pnpm run quality", ("quality", "lint", "build", "test", "pytest", "vitest"))]
    if template_id == TaskTemplateId.REVIEW:
        return [_review_check(closure)]
    return [_change_check(closure, "变更或工具证据", None), _quality_check(closure, "测试或质量门证据", "pytest 或 pnpm test", ("quality", "lint", "build", "test", "pytest", "vitest"))]


def _change_check(closure: TaskClosure, label: str, keyword: str | None) -> VerificationCheck:
    changed = bool(closure.changed_files)
    evidence = ", ".join(closure.changed_files)
    if keyword and not changed:
        changed = _contains(closure.command_results + closure.commands, (keyword,))
        evidence = _first_match(closure.command_results + closure.commands, (keyword,))
    tool_evidence = _contains(closure.commands, ("tool:",)) or _contains(closure.command_results, ("file", "write", "patch", "读取"))
    satisfied = changed or (keyword is None and tool_evidence)
    return VerificationCheck("change", label, None, True, satisfied, evidence, f"缺少{label}")


def _test_change_check(closure: TaskClosure) -> VerificationCheck:
    items = closure.changed_files + closure.commands + closure.command_results
    satisfied = _contains(items, ("test", "pytest", "vitest"))
    evidence = _first_match(items, ("test", "pytest", "vitest"))
    return VerificationCheck("test-change", "测试变更证据", None, True, satisfied, evidence, "缺少测试变更或测试命令证据")


def _quality_check(closure: TaskClosure, label: str, command: str, keywords: tuple[str, ...]) -> VerificationCheck:
    evidence_items = closure.commands + closure.command_results
    has_gate = _contains(evidence_items, keywords)
    has_success = _has_success_evidence(closure.command_results)
    has_failure = _has_failure_evidence(closure.command_results)
    satisfied = has_gate and has_success and not has_failure
    return VerificationCheck("quality", label, command, True, satisfied, _first_match(evidence_items, keywords), f"缺少{label}")


def _review_check(closure: TaskClosure) -> VerificationCheck:
    summary = closure.review_summary.strip()
    passed = bool(summary) and _has_success_evidence([summary]) and not _has_failure_evidence([summary])
    return VerificationCheck("review", "审查通过证据", None, True, passed, summary, "缺少通过的审查摘要")


def _repair_suggestions(closure: TaskClosure) -> list[str]:
    if closure.status == TaskClosureStatus.FAILED:
        return ["根据失败输出修复问题后重新记录验证证据"]
    return ["补充缺少的验证证据后重新评估完成度"]


def _has_success_evidence(items: list[str]) -> bool:
    return _contains(items, ("passed", "pass", "通过", "0 failed", "成功"))


def _has_failure_evidence(items: list[str]) -> bool:
    normalized = [item.lower() for item in items]
    for item in normalized:
        if "not passed" in item or "未通过" in item or "失败" in item or "error" in item:
            return True
        if "failed" in item and "0 failed" not in item:
            return True
        if "fail" in item and "0 failed" not in item:
            return True
    return False


def _contains(items: list[str], keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in item.lower() for item in items for keyword in keywords)


def _first_match(items: list[str], keywords: tuple[str, ...]) -> str:
    for item in items:
        if any(keyword.lower() in item.lower() for keyword in keywords):
            return item
    return ""
