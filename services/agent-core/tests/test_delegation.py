from bolt_core.delegation import (
    AgentRole, DelegationTask, DelegationService, TaskStatus,
)


def test_delegation_task_lifecycle(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(
        role=AgentRole.BUILDER, objective="Implement auth module",
        inputs={"files": ["auth.py"]}, constraints=["no external deps"])

    assert task.status == TaskStatus.PENDING
    assert task.role == AgentRole.BUILDER

    # Start
    started = svc.start(task.id)
    assert started.status == TaskStatus.RUNNING

    # Complete with evidence
    completed = svc.complete(task.id, output="auth.py created",
                             evidence=["test_auth.py passed"])
    assert completed.status == TaskStatus.COMPLETED
    assert len(completed.evidence) == 1


def test_delegation_task_fail(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(role=AgentRole.BUILDER, objective="Fix bug")
    started = svc.start(task.id)
    failed = svc.fail(task.id, reason="timeout exceeded")
    assert failed.status == TaskStatus.FAILED


def test_delegation_scope_constraint(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(
        role=AgentRole.RESEARCHER, objective="Research frameworks",
        constraints=["read_only", "scope:python"])

    # Task should track constraints
    assert "read_only" in task.constraints
    assert "scope:python" in task.constraints


def test_delegation_reviewer_fail_blocks_promotion(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    build_task = svc.create(role=AgentRole.BUILDER, objective="Build feature")
    svc.start(build_task.id)
    svc.complete(build_task.id, output="feature built", evidence=["tests pass"])

    # Reviewer task
    review_task = svc.create(
        role=AgentRole.REVIEWER, objective="Review build",
        inputs={"review_of": build_task.id})
    svc.start(review_task.id)
    svc.fail(review_task.id, reason="security issue found")

    # Original build task should be marked as needing revision
    updated_build = svc.get(build_task.id)
    assert updated_build.status == TaskStatus.NEEDS_REVISION


def test_delegation_sub_task_cannot_expand_workspace(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(
        role=AgentRole.BUILDER, objective="Fix bug",
        constraints=["workspace:/project/src"])

    # Task should record workspace boundary
    assert task.workspace == "/project/src"


def test_delegation_evidence_required_for_completion(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(role=AgentRole.BUILDER, objective="Fix bug")
    svc.start(task.id)

    # Complete without evidence should fail
    import pytest
    with pytest.raises(ValueError, match="evidence"):
        svc.complete(task.id, output="done", evidence=[])


def test_delegation_list_by_role(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    svc.create(role=AgentRole.PLANNER, objective="Plan sprint")
    svc.create(role=AgentRole.BUILDER, objective="Build feature")
    svc.create(role=AgentRole.BUILDER, objective="Fix bug")

    builders = svc.list_by_role(AgentRole.BUILDER)
    assert len(builders) == 2

    planners = svc.list_by_role(AgentRole.PLANNER)
    assert len(planners) == 1


def test_delegation_results_back_to_trace(tmp_path):
    svc = DelegationService(workspace=str(tmp_path))
    task = svc.create(role=AgentRole.BUILDER, objective="Build X")
    svc.start(task.id)
    result = svc.complete(task.id, output="X built",
                          evidence=["tests pass"])

    # Result should be retrievable
    retrieved = svc.get(task.id)
    assert retrieved.output == "X built"
    assert "tests pass" in retrieved.evidence
