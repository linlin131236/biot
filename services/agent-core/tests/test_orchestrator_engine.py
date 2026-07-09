"""Tests for OrchestratorEngine: 5-role pipeline wiring."""
import pytest

from bolt_core.orchestrator_engine import OrchestratorEngine, OrchestrationResult
from bolt_core.builder_engine import BuilderEngine, BuilderTask
from bolt_core.reviewer_engine import ReviewerEngine
from bolt_core.multi_agent_workflow_models import BuilderOutput


def test_orchestrator_runs_pipeline():
    builder = BuilderEngine(workspace=".")
    reviewer = ReviewerEngine()
    engine = OrchestratorEngine(builder=builder, reviewer=reviewer)
    result = engine.orchestrate("添加类型检查", "services/agent-core/src/bolt_core/approval_apply.py")
    assert isinstance(result, OrchestrationResult)
    assert result.rounds >= 1
    assert result.final_verdict in ("approved", "blocked", "failed")


def test_orchestrator_tracks_trace():
    builder = BuilderEngine(workspace=".")
    reviewer = ReviewerEngine()
    engine = OrchestratorEngine(builder=builder, reviewer=reviewer)
    result = engine.orchestrate("测试任务", "services/agent-core/src/bolt_core/approval_apply.py")
    roles_in_trace = [step["role"] for step in result.trace]
    assert "builder" in roles_in_trace
    assert "reviewer" in roles_in_trace


def test_orchestrator_approved_when_clean():
    builder = BuilderEngine(workspace=".")
    reviewer = ReviewerEngine()
    engine = OrchestratorEngine(builder=builder, reviewer=reviewer)
    result = engine.orchestrate("添加简单注释", "services/agent-core/src/bolt_core/approval_apply.py")
    # Clean code should get approved
    assert result.final_verdict == "approved"


def test_orchestrator_reviewer_in_trace():
    builder = BuilderEngine(workspace=".")
    reviewer = ReviewerEngine()
    engine = OrchestratorEngine(builder=builder, reviewer=reviewer)
    result = engine.orchestrate("测试审查员", "services/agent-core/src/bolt_core/approval_apply.py")
    roles_in_trace = [step["role"] for step in result.trace]
    assert "reviewer" in roles_in_trace
    assert "builder" in roles_in_trace


def test_orchestrator_respects_max_rounds():
    builder = BuilderEngine(workspace=".")
    reviewer = ReviewerEngine()
    engine = OrchestratorEngine(builder=builder, reviewer=reviewer)
    # Force blocked verdict by providing risky code
    result = engine.orchestrate("使用 ipcRenderer", "services/agent-core/src/bolt_core/approval_apply.py")
    assert result.rounds <= engine._MAX_REVIEW_ROUNDS
    assert engine._MAX_REVIEW_ROUNDS == 5


def test_orchestrator_max_rounds_is_five():
    engine = OrchestratorEngine()
    assert engine._MAX_REVIEW_ROUNDS == 5


def test_orchestrator_without_reviewer_auto_approves():
    builder = BuilderEngine(workspace=".")
    engine = OrchestratorEngine(builder=builder, reviewer=None)
    result = engine.orchestrate("简单任务", "services/agent-core/src/bolt_core/approval_apply.py")
    assert result.final_verdict == "approved"
