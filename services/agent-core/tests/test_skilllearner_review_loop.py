"""Tests for SkillLearnerReviewLoopService."""
from bolt_core.skilllearner_review_loop import SkillLearnerReviewLoopService


def test_record_failure():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("test_timeout", "f1", "测试超时")
    assert svc.total_failures() == 1


def test_analyze_below_threshold():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("test_timeout", "f1", "超时")
    result = svc.analyze()
    assert result["patterns_found"] is False


def test_analyze_above_threshold():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("test_timeout", "f1", "超时1")
    svc.record_failure("test_timeout", "f2", "超时2")
    result = svc.analyze()
    assert result["patterns_found"] is True


def test_propose_improvement():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("test_timeout", "f1", "超时1")
    svc.record_failure("test_timeout", "f2", "超时2")
    proposal = svc.propose_improvement("改进测试超时", "test_timeout", target_type="workflow_doc")
    assert proposal.requires_father_approval is True
    assert proposal.proposal_id.startswith("prop-")
    assert len(proposal.options) == 3


def test_list_proposals():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("t", "f1", "d")
    svc.record_failure("t", "f2", "d")
    svc.propose_improvement("test", "t")
    assert len(svc.list_proposals()) == 1


def test_proposal_note_mentions_father():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("t", "f1", "d")
    svc.record_failure("t", "f2", "d")
    p = svc.propose_improvement("test", "t")
    assert "爸爸" in p.to_dict()["note"] or "father" in p.to_dict()["note"].lower()


def test_proposal_target_types():
    svc = SkillLearnerReviewLoopService()
    svc.record_failure("t", "f1", "d")
    svc.record_failure("t", "f2", "d")
    for tt in ["workflow_doc", "skill_doc", "review_policy"]:
        p = svc.propose_improvement(f"test-{tt}", "t", target_type=tt)
        assert p.target_type == tt
