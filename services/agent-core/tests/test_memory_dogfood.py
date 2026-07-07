"""Tests for MemoryDogfoodService."""
import pytest

from bolt_core.memory_dogfood import MemoryDogfoodService, DogfoodResult, DogfoodCheck


def test_dogfood_result_fields():
    checks = [
        DogfoodCheck(name="test1", passed=True, detail_cn="通过", source_refs=["ref1"]),
        DogfoodCheck(name="test2", passed=False, detail_cn="失败", source_refs=["ref2"]),
    ]
    result = DogfoodResult(
        phase="M80",
        checks=checks,
        summary_cn="测试摘要",
        ready_for_next=False,
    )
    d = result.to_dict()
    assert d["phase"] == "M80"
    assert d["total_checks"] == 2
    assert d["passed_checks"] == 1
    assert d["failed_checks"] == 1
    assert d["ready_for_next"] is False


def test_dogfood_check_is_frozen():
    check = DogfoodCheck(name="t", passed=True, detail_cn="ok", source_refs=["r"])
    with pytest.raises(Exception):
        check.passed = False  # type: ignore[misc]


def test_assess_returns_result():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    assert isinstance(result, DogfoodResult)
    assert result.phase == "M80"
    assert len(result.checks) >= 10  # At least 10 checks


def test_assess_all_checks_have_names():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    for c in result.checks:
        assert c.name != ""


def test_assess_all_checks_have_details():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    for c in result.checks:
        assert c.detail_cn != ""


def test_assess_m71_check_exists():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    m71 = [c for c in result.checks if "M71" in c.name]
    assert len(m71) == 1


def test_assess_m78_check_exists():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    m78 = [c for c in result.checks if "M78" in c.name]
    assert len(m78) == 1


def test_assess_no_m81_check_exists():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    no_m81 = [c for c in result.checks if "M81" in c.name or "未进入" in c.detail_cn]
    assert len(no_m81) >= 1


def test_assess_no_auto_execution_check():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    auto_check = [c for c in result.checks if "自动执行" in c.name]
    assert len(auto_check) == 1


def test_assess_source_refs_check():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    refs_check = [c for c in result.checks if "source_refs" in c.name.lower()]
    assert len(refs_check) == 1


def test_dogfood_chinese_output():
    svc = MemoryDogfoodService(".")
    result = svc.assess()
    assert any('\u4e00' <= c <= '\u9fff' for c in result.summary_cn)
