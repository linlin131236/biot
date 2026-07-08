"""Tests for BuilderEngine: code change proposals, no direct writes."""
import pytest

from bolt_core.builder_engine import BuilderEngine, BuilderTask
from bolt_core.multi_agent_workflow_models import BuilderOutput


def test_builder_engine_produces_proposals():
    engine = BuilderEngine(workspace=".")
    task = BuilderTask(
        task_id="task_1",
        description_cn="添加类型检查",
        target_files=["services/agent-core/src/bolt_core/approval_apply.py"],
        workspace=".",
    )
    output = engine.execute_task(task)
    assert isinstance(output, BuilderOutput)
    assert len(output.evidence_refs) > 0
    assert "workspace:." in output.source_refs


def test_builder_engine_respects_path_guard():
    engine = BuilderEngine(workspace=".")
    task = BuilderTask(
        task_id="task_2",
        description_cn="尝试写入禁止路径",
        target_files=["/etc/passwd"],
        workspace=".",
    )
    output = engine.execute_task(task)
    assert isinstance(output, BuilderOutput)
    # PathGuard should block /etc/passwd
    assert len(output.evidence_refs) == 0


def test_builder_engine_determines_test_commands():
    engine = BuilderEngine(workspace=".")
    task = BuilderTask(
        task_id="task_3",
        description_cn="添加测试",
        target_files=["src/App.tsx", "src/app.py"],
        workspace=".",
    )
    output = engine.execute_task(task)
    assert "vitest" in output.tests
    assert "pytest" in output.tests


def test_builder_engine_get_proposal():
    engine = BuilderEngine(workspace=".")
    task = BuilderTask(
        task_id="task_4",
        description_cn="测试",
        target_files=["services/agent-core/src/bolt_core/approval_apply.py"],
        workspace=".",
    )
    engine.execute_task(task)
    proposal = engine.get_proposal("services/agent-core/src/bolt_core/approval_apply.py")
    assert proposal is not None
    assert proposal.status in ("pending_review", "failed")


def test_builder_engine_list_proposals():
    engine = BuilderEngine(workspace=".")
    task = BuilderTask(
        task_id="task_5",
        description_cn="测试",
        target_files=["services/agent-core/src/bolt_core/approval_apply.py"],
        workspace=".",
    )
    engine.execute_task(task)
    proposals = engine.list_proposals()
    assert len(proposals) > 0


def test_builder_engine_does_not_approve_permissions():
    engine = BuilderEngine(workspace=".")
    assert not hasattr(engine, "approve_permission")
    assert not hasattr(engine, "push")
    assert not hasattr(engine, "release")
