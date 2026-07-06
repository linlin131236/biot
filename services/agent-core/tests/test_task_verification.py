from bolt_core.task_closure import TaskClosureStatus, TaskTemplateId
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.task_verification import assess_completion, build_verification_plan


def test_bugfix_changed_files_and_pytest_passed():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")
    svc.record_command(closure.id, "pytest", "12 passed")

    assessment = assess_completion(closure)

    assert assessment.status == "passed"
    assert assessment.missing == []


def test_bugfix_without_test_evidence_missing():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")

    assessment = assess_completion(closure)

    assert assessment.status == "missing_evidence"
    assert "缺少测试或质量门证据" in assessment.missing


def test_docs_with_docs_lint_passed():
    svc = TaskClosureService()
    closure = svc.start("更新文档", TaskTemplateId.DOCS)
    svc.record_file_change(closure.id, "docs/readme.md")
    svc.record_command(closure.id, "pnpm lint:docs", "docs lint 通过")

    assessment = assess_completion(closure)

    assert assessment.status == "passed"


def test_pending_permission_waiting_permission():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.mark_waiting_permission(closure.id, "perm_1")

    assessment = assess_completion(closure)

    assert assessment.status == "waiting_permission"


def test_stopped_status_stays_stopped():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_loop_status(closure.id, "max_steps_reached")

    assessment = assess_completion(closure)

    assert assessment.status == "stopped"


def test_failed_status_needs_repair():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.mark_failed(closure.id, "pytest failed")

    assessment = assess_completion(closure)

    assert assessment.status == "needs_repair"
    assert assessment.repair_suggestions


def test_review_without_summary_missing():
    svc = TaskClosureService()
    closure = svc.start("审查", TaskTemplateId.REVIEW)

    assessment = assess_completion(closure)

    assert assessment.status == "missing_evidence"
    assert "缺少通过的审查摘要" in assessment.missing


def test_review_passed_summary_passes():
    svc = TaskClosureService()
    closure = svc.start("审查", TaskTemplateId.REVIEW)
    svc.record_review(closure.id, "审查通过", True)

    assessment = assess_completion(closure)

    assert assessment.status == "passed"


def test_pytest_not_passed_does_not_pass():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")
    svc.record_command(closure.id, "pytest", "not passed")

    assessment = assess_completion(closure)

    assert assessment.status == "missing_evidence"


def test_pytest_failed_output_does_not_pass():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")
    svc.record_command(closure.id, "pytest", "1 failed, 0 passed")

    assessment = assess_completion(closure)

    assert assessment.status == "missing_evidence"


def test_review_unpassed_summary_does_not_pass():
    svc = TaskClosureService()
    closure = svc.start("审查", TaskTemplateId.REVIEW)
    svc.record_review(closure.id, "未通过", False)

    assessment = assess_completion(closure)

    assert assessment.status == "missing_evidence"


def test_zero_failed_still_counts_as_success():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)
    svc.record_file_change(closure.id, "src/app.py")
    svc.record_command(closure.id, "pytest", "12 passed, 0 failed")

    assessment = assess_completion(closure)

    assert assessment.status == "passed"


def test_plan_contains_command_suggestion_without_execution():
    svc = TaskClosureService()
    closure = svc.start("修复拼写", TaskTemplateId.BUGFIX)

    plan = build_verification_plan(closure)

    assert plan.checks[1].command == "pytest 或 pnpm test"
    assert svc.to_dict(closure.id)["commands"] == []
