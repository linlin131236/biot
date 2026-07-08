"""Tests for ReviewerEngine: strict gate enforcement."""
import pytest

from bolt_core.reviewer_engine import ReviewerEngine
from bolt_core.multi_agent_workflow_models import BuilderOutput


def test_reviewer_clean_output_returns_approved():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="+ x = 1",
        tests="pytest test.py",
        evidence_refs=["ref-1"],
        source_refs=["src-1"],
    )
    result = engine.review_output(output)
    assert result.verdict == "approved"


def test_reviewer_p0_finding_blocks_approval():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="ipcRenderer.send('msg')",
        tests="pytest test.py",
        evidence_refs=["ref-1"],
        source_refs=["src-1"],
    )
    result = engine.review_output(output)
    assert result.verdict == "blocked"
    assert any(f["severity"] == "P0" for f in result.findings)


def test_reviewer_p1_finding_blocks_approval():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="subprocess.run(['cmd'], shell=True)",
        tests="",
        evidence_refs=[],
        source_refs=[],
    )
    result = engine.review_output(output)
    assert result.verdict == "blocked"
    assert any(f["severity"] == "P1" for f in result.findings)


def test_reviewer_p2_finding_triggers_changes_requested():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="const x: any = 1",
        tests="",
        evidence_refs=["ref-1"],
        source_refs=["src-1"],
    )
    result = engine.review_output(output)
    assert result.verdict == "changes_requested"
    assert any(f["severity"] == "P2" for f in result.findings)


def test_reviewer_missing_evidence_refs_is_p1():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="+ x = 1",
        tests="pytest test.py",
        evidence_refs=[],
        source_refs=["src-1"],
    )
    result = engine.review_output(output)
    assert result.verdict == "blocked"
    assert any(f["severity"] == "P1" and "evidence" in f["description"].lower() for f in result.findings)


def test_reviewer_missing_tests_is_p2():
    engine = ReviewerEngine()
    output = BuilderOutput(
        code_changes="+ x = 1",
        tests="(no tests specified)",
        evidence_refs=["ref-1"],
        source_refs=["src-1"],
    )
    result = engine.review_output(output)
    assert result.verdict == "changes_requested"
    assert any(f["severity"] == "P2" and "测试" in f["description"] for f in result.findings)


def test_reviewer_does_not_execute_tools():
    engine = ReviewerEngine()
    assert not hasattr(engine, "execute_tool")
    assert not hasattr(engine, "push")
    assert not hasattr(engine, "release")
    assert not hasattr(engine, "approve_permission")
