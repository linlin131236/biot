"""Tests for DesktopBetaDogfoodService."""
import pytest
from bolt_core.desktop_beta_dogfood import DesktopBetaDogfoodService, DogfoodResult


def test_all_checks_pass():
    svc = DesktopBetaDogfoodService()
    result = svc.run()
    assert result.total == 13
    assert result.passed == 13
    assert result.failed == 0
    assert result.ready_for_next is True


def test_summary_is_chinese():
    svc = DesktopBetaDogfoodService()
    result = svc.run()
    assert any('\u4e00' <= c <= '\u9fff' for c in result.summary_cn)


def test_to_dict():
    svc = DesktopBetaDogfoodService()
    result = svc.run()
    d = result.to_dict()
    assert d["total"] == 13
    assert d["ready_for_next"] is True
    assert len(d["checks"]) == 13
    for c in d["checks"]:
        assert "check_id" in c
        assert "label_cn" in c
        assert "passed" in c
        assert c["passed"] is True


def test_check_structure():
    svc = DesktopBetaDogfoodService()
    result = svc.run()
    ids = [c.check_id for c in result.checks]
    assert "m91_task_home" in ids
    assert "m92_permission_center" in ids
    assert "cross_chinese_ui" in ids
    assert "cross_not_entered_m101" in ids
