"""Tests for ProjectProfileService."""
import pytest

from bolt_core.project_profile import ProjectProfileService, ProjectProfile


def test_build_returns_profile():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert isinstance(profile, ProjectProfile)
    assert profile.project_name != ""
    assert profile.workspace_path != ""


def test_profile_has_project_name():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert len(profile.project_name) > 0


def test_profile_has_current_milestone():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert profile.current_milestone != ""
    assert "M6" in profile.current_milestone or "M7" in profile.current_milestone or "未知" in profile.current_milestone


def test_profile_has_latest_head():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert profile.latest_head != ""


def test_profile_has_hard_rules():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert len(profile.hard_rules) > 0


def test_profile_has_source_refs():
    svc = ProjectProfileService(".")
    profile = svc.build()
    assert len(profile.source_refs) > 0


def test_profile_to_dict():
    svc = ProjectProfileService(".")
    profile = svc.build()
    d = profile.to_dict()
    keys = ["project_name", "workspace_path", "current_milestone",
            "latest_head", "origin_state", "tech_stack", "key_commands",
            "hard_rules", "important_docs", "latest_review_gate",
            "known_risks", "source_refs"]
    for key in keys:
        assert key in d, f"missing: {key}"


def test_profile_no_secret_in_output():
    """Profile must not contain secret paths or content."""
    svc = ProjectProfileService(".")
    profile = svc.build()
    d = profile.to_dict()
    text = str(d).lower()
    assert ".env" not in text or "文档" in str(d.get("important_docs"))
    assert "password" not in text
    assert "secret" not in text


def test_profile_chinese_in_milestone():
    svc = ProjectProfileService(".")
    profile = svc.build()
    # Should have some Chinese characters
    assert any('\u4e00' <= c <= '\u9fff' for c in str(profile.to_dict()))


def test_missing_docs_degraded():
    """When project-state is missing, profile should degrade gracefully."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        svc = ProjectProfileService(tmp)
        profile = svc.build()
        assert "缺失" in profile.current_milestone or "未知" in profile.current_milestone
