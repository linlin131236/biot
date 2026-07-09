"""Reviewer self-review auto-fix proposal service."""
from __future__ import annotations


class AutoFixService:
    """Auto-resolve only low-risk review findings and return a proposal summary.

    This service does not write files. It marks which findings can be handled
    automatically and leaves P0/P1/security items for human review.
    """

    def auto_fix(self, findings: list[dict], code_changes: str) -> dict:
        if not findings:
            return {
                "fixed": 0,
                "remaining": 0,
                "fixed_items": [],
                "remaining_items": [],
                "message": "没有需要自动修复的审查发现",
            }

        fixed_items: list[dict] = []
        remaining_items: list[dict] = []
        result_code = code_changes

        for finding in findings:
            severity = str(finding.get("severity", "")).upper()
            description = str(finding.get("description", ""))
            if severity == "P2" and self._is_low_risk(description):
                fixed_items.append({**finding, "auto_fix": "可由低风险规则处理"})
                result_code = self._rewrite_low_risk_patterns(result_code)
            else:
                remaining_items.append({**finding, "reason": "需要人工审查或不属于低风险修复"})

        return {
            "fixed": len(fixed_items),
            "remaining": len(remaining_items),
            "fixed_items": fixed_items,
            "remaining_items": remaining_items,
            "proposed_code": result_code,
            "message": "自动修复仅生成低风险提案，未直接写入文件",
        }

    @staticmethod
    def _is_low_risk(description: str) -> bool:
        lowered = description.lower()
        return any(keyword in lowered for keyword in ["trailing whitespace", "文档", "测试说明", "copy"])

    @staticmethod
    def _rewrite_low_risk_patterns(code_changes: str) -> str:
        return "\n".join(line.rstrip() for line in code_changes.splitlines())
