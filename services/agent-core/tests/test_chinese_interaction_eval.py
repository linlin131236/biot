"""Tests for ChineseInteractionEvalService (M117)."""
import pytest
from bolt_core.chinese_interaction_eval import ChineseInteractionEvalService


class TestChineseInteractionEval:
    def test_at_least_12_samples(self):
        samples = ChineseInteractionEvalService._samples()
        assert len(samples) >= 12, f"需要≥12，当前{len(samples)}"

    def test_run_all(self):
        summary = ChineseInteractionEvalService.run_all()
        assert summary.total_cases >= 12
        # 13 samples: 10 pass + 3 fail (english-only, mojibake, protocol leak)
        assert summary.passed == 10, f"期望10个通过，实际{summary.passed}"

    def test_chinese_text_passes(self):
        r = ChineseInteractionEvalService.check("这是中文文本，用于测试。")
        assert r.passed is True
        assert r.is_chinese is True

    def test_english_only_fails(self):
        r = ChineseInteractionEvalService.check("Error: something went wrong with the operation")
        assert r.no_english_only is False

    def test_mojibake_fails(self):
        r = ChineseInteractionEvalService.check("工具\x00调用\x1f评估")
        assert r.no_mojibake is False

    def test_protocol_leak_fails(self):
        r = ChineseInteractionEvalService.check('{"tool": "write_file", "operation": "modify"}')
        assert r.no_protocol_leak is False

    def test_has_chinese(self):
        assert ChineseInteractionEvalService.has_chinese("中文字符") is True
        assert ChineseInteractionEvalService.has_chinese("English only") is False

    def test_summary_to_dict(self):
        summary = ChineseInteractionEvalService.run_all()
        d = summary.to_dict()
        assert d["all_passed"] is False  # 3 deliberate failures
        assert d["passed"] == 10
        assert d["failed"] == 3
