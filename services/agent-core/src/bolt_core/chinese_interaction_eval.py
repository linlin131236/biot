"""Chinese Interaction Quality Eval (M117). Verify Chinese UI/API text quality.

Checks for Chinese content, mojibake absence, tool protocol leakage,
and English-only user-visible text. Structured output, read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

# ── Patterns ──

_MOJIBAKE_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufffd\ufffe\uffff]')
_TOOL_PROTOCOL_PATTERNS = [
    r'```json\s*\{[^}]*"tool"\s*:',   # tool call JSON in text
    r'<tool_call>', r'</tool_call>',
    r'<function_call>', r'</function_call>',
    r'"tool"\s*:\s*"',                 # raw tool key in JSON
    r'"operation"\s*:\s*"',            # raw operation key in JSON
]


@dataclass(frozen=True)
class ChineseInteractionSample:
    case_id: str; source: str  # "api" / "ui" / "doc"
    text: str; description: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "source": self.source,
                "description": self.description, "text_preview": self.text[:100]}


@dataclass(frozen=True)
class ChineseInteractionResult:
    case_id: str; passed: bool; is_chinese: bool; no_mojibake: bool
    no_protocol_leak: bool; no_english_only: bool; notes: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "is_chinese": self.is_chinese, "no_mojibake": self.no_mojibake,
                "no_protocol_leak": self.no_protocol_leak,
                "no_english_only": self.no_english_only, "notes": self.notes}


@dataclass
class ChineseInteractionSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[ChineseInteractionResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "中文交互质量评估仅检查文本质量，不修改任何内容。"}


class ChineseInteractionEvalService:
    """M117 中文交互质量评估服务。"""

    @staticmethod
    def has_chinese(text: str) -> bool:
        """Check if text contains at least one Chinese character."""
        return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))

    @staticmethod
    def check(text: str) -> ChineseInteractionResult:
        is_cn = ChineseInteractionEvalService.has_chinese(text)
        no_moji = not bool(_MOJIBAKE_PATTERN.search(text))
        no_proto = True
        for pat in _TOOL_PROTOCOL_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                no_proto = False
                break
        # Check for English-only lines (no Chinese chars, not code, > 3 words)
        no_eng_only = True
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '//', '`', '{', '}', 'import ', 'from ', 'def ', 'class ')):
                continue
            # Has Chinese? Skip
            if ChineseInteractionEvalService.has_chinese(stripped):
                continue
            # Count English words
            words = [w for w in re.findall(r'[a-zA-Z]+', stripped) if len(w) > 1]
            if len(words) >= 4:
                no_eng_only = False
                break

        passed = is_cn and no_moji and no_proto and no_eng_only
        notes_parts = []
        if not is_cn: notes_parts.append("缺少中文")
        if not no_moji: notes_parts.append("含乱码")
        if not no_proto: notes_parts.append("工具协议泄漏")
        if not no_eng_only: notes_parts.append("英文only文案")

        return ChineseInteractionResult(
            case_id="", passed=passed, is_chinese=is_cn,
            no_mojibake=no_moji, no_protocol_leak=no_proto,
            no_english_only=no_eng_only,
            notes="; ".join(notes_parts) if notes_parts else "全部通过",
        )

    @staticmethod
    def run_all() -> ChineseInteractionSummary:
        results = []
        for sample in ChineseInteractionEvalService._samples():
            r = ChineseInteractionEvalService.check(sample.text)
            r = ChineseInteractionResult(
                case_id=sample.case_id, passed=r.passed,
                is_chinese=r.is_chinese, no_mojibake=r.no_mojibake,
                no_protocol_leak=r.no_protocol_leak,
                no_english_only=r.no_english_only, notes=r.notes,
            )
            results.append(r)
        p = sum(1 for r in results if r.passed)
        return ChineseInteractionSummary(total_cases=len(results), passed=p,
                                         failed=len(results) - p, results=results)

    @staticmethod
    def _samples() -> list[ChineseInteractionSample]:
        CS = ChineseInteractionSample
        return [
            CS("api_tool_eval", "api", "工具调用评估仅验证工具选择和权限判断的正确性，不执行任何真实工具操作。"),
            CS("api_patch_eval", "api", "补丁应用评估在临时目录中运行，不修改真实项目文件。"),
            CS("api_perm_boundary", "api", "权限边界评估仅验证 PermissionContractEngine 决策正确性，不执行任何真实操作。"),
            CS("api_multi_agent", "api", "多Agent协作评估仅验证角色边界定义，不执行真实Agent操作。"),
            CS("api_memory", "api", "记忆检索评估使用fixture数据，不访问真实记忆存储。"),
            CS("ui_patch_preview", "ui", "补丁预览：以下是将要应用的代码变更，请爸爸审查后批准。"),
            CS("ui_permission_center", "ui", "权限中心：当前有待处理的权限请求，请爸爸审核并决定批准或拒绝。"),
            CS("ui_task_home", "ui", "任务首页：Bolt Agent 正在监控项目变更，等待爸爸的指令。"),
            CS("ui_audit_timeline", "ui", "审计时间线：展示最近的操作记录和审计结果。"),
            CS("doc_review_gate", "doc", "评估验证失败分类和脱敏，不自动修复任何问题（is_auto_fix_allowed=false）。"),
            CS("api_avoid_english_only", "api", "Error: something went wrong"),  # should fail
            CS("api_avoid_mojibake", "api", "工具\x00调用\x1f评估"),  # should fail for mojibake
            CS("api_avoid_protocol", "api", '{"tool": "write_file", "operation": "modify"}'),  # should fail
        ]
