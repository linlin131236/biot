"""Tests for TeamDogfoodService."""
from bolt_core.team_dogfood import TeamDogfoodService


def test_dogfood_runs_all_checks():
    svc = TeamDogfoodService()
    result = svc.run()
    assert result.total == 12  # 9 component + 3 cross-cutting
    assert result.passed >= 9  # most should pass on a healthy system


def test_dogfood_returns_summary():
    svc = TeamDogfoodService()
    result = svc.run()
    assert "大复盘" in result.summary_cn or "通过" in result.summary_cn


def test_dogfood_to_dict():
    svc = TeamDogfoodService()
    result = svc.run()
    d = result.to_dict()
    assert "checks" in d
    assert "ready_for_next" in d
    assert len(d["checks"]) == 12
