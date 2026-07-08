"""ReviewerEngine: reads Builder output and produces structured review findings.
Strict Gate: P0/P1 block approval, P2 triggers changes_requested.

M161: Reviewer execution engine with independent gate enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from bolt_core.multi_agent_workflow_models import ReviewerOutput, BuilderOutput


@dataclass
class ReviewFinding:
    """A single review finding."""
    finding_id: str
    severity: str  # P0, P1, P2
    category_cn: str  # 安全, 质量, 规范, 性能
    description_cn: str
    location: str  # file:line or "general"
    suggestion_cn: str


class ReviewerEngine:
    """Reads Builder output and produces structured review findings.
    Enforces strict gate: P0/P1 block, P2 changes_requested.
    """

    def __init__(self) -> None:
        self._findings: list[ReviewFinding] = []

    def review_output(self, builder_output: BuilderOutput, code_changes: str = "") -> ReviewerOutput:
        """Review builder output and produce structured findings.

        Strict Gate rules:
        - P0 (critical): blocks approval immediately
        - P1 (major): blocks approval
        - P2 (minor): triggers changes_requested
        - No findings: approved
        """
        if not code_changes:
            code_changes = builder_output.code_changes
        findings: list[dict] = []
        self._findings = []

        # Analyze code_changes for risks
        if code_changes:
            findings.extend(self._scan_for_risks(code_changes))

        # Analyze evidence_refs for completeness
        if not builder_output.evidence_refs:
            findings.append({
                "severity": "P1",
                "category": "规范",
                "description": "缺少证据引用（evidence_refs）",
                "location": "general",
                "suggestion": "Builder 必须提供证据引用，证明变更基于可靠来源。",
            })

        # Analyze tests for completeness
        if not builder_output.tests or builder_output.tests == "(no tests specified)":
            findings.append({
                "severity": "P2",
                "category": "质量",
                "description": "未指定测试验证方案",
                "location": "general",
                "suggestion": "为代码变更添加对应的测试命令或验证步骤。",
            })

        # Determine verdict based on strict gate
        verdict = self._determine_verdict(findings)

        evidence_refs = [f.finding_id for f in self._findings]
        source_refs = builder_output.source_refs

        return ReviewerOutput(
            findings=findings,
            evidence=evidence_refs,
            tests_status=builder_output.tests,
            residual_risks=[],
            verdict=verdict,
            source_refs=source_refs,
        )

    def _scan_for_risks(self, code_changes: str) -> list[dict]:
        """Scan code changes for security and quality risks."""
        findings = []
        risk_patterns = [
            ("ipcRenderer", "P0", "renderer 暴露风险", "安全", "前端代码直接引用 ipcRenderer，违反安全规范。请通过 preload bridge 访问 Node API。"),
            ("process.", "P0", "process 暴露风险", "安全", "前端代码直接引用 process 对象，违反安全规范。请通过 preload bridge 访问。"),
            ("require(", "P0", "动态 require 风险", "安全", "前端代码使用动态 require，可能加载未授权模块。请使用静态 import。"),
            ("as any", "P2", "类型绕过", "规范", "使用 as any 绕过 TypeScript 类型检查。请使用正确的类型断言。"),
            ("unknown as", "P2", "类型绕过", "规范", "使用 unknown as 绕过 TypeScript 类型检查。请使用正确的类型断言。"),
            ("push", "P1", "自动 push 风险", "安全", "代码包含 push 操作，需要人工确认。"),
            ("release", "P1", "自动 release 风险", "安全", "代码包含 release 操作，需要人工确认。"),
            ("tag", "P1", "自动 tag 风险", "安全", "代码包含 tag 操作，需要人工确认。"),
            ("delete", "P1", "自动 delete 风险", "安全", "代码包含 delete 操作，需要人工确认。"),
            ("eval(", "P0", "eval 注入风险", "安全", "代码使用 eval()，存在代码注入风险。请避免使用 eval。"),
            ("subprocess", "P1", "子进程执行风险", "安全", "代码包含 subprocess 调用，需要审批。"),
            ("shell=True", "P1", "shell 注入风险", "安全", "代码使用 shell=True，存在命令注入风险。请使用数组参数。"),
        ]

        lines = code_changes.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern, severity, title, category, suggestion in risk_patterns:
                if pattern in line:
                    finding_id = f"find-{len(self._findings):03d}"
                    self._findings.append(ReviewFinding(
                        finding_id=finding_id,
                        severity=severity,
                        category_cn=category,
                        description_cn=f"{title}：{line.strip()[:80]}",
                        location=f"line-{i}",
                        suggestion_cn=suggestion,
                    ))
                    findings.append({
                        "finding_id": finding_id,
                        "severity": severity,
                        "category": category,
                        "description": f"{title}：{line.strip()[:80]}",
                        "location": f"line-{i}",
                        "suggestion": suggestion,
                    })
                    break  # One finding per line

        return findings

    def _determine_verdict(self, findings: list[dict]) -> str:
        """Determine verdict based on strict gate rules."""
        has_p0 = any(f["severity"] == "P0" for f in findings)
        has_p1 = any(f["severity"] == "P1" for f in findings)
        has_p2 = any(f["severity"] == "P2" for f in findings)

        if has_p0 or has_p1:
            return "blocked"
        if has_p2:
            return "changes_requested"
        return "approved"
