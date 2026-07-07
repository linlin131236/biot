"""Patch Apply Eval (M112). Evaluate M108 ApprovalApplyEngine safety and correctness.

Runs eval cases in temporary directories to verify patch application handles:
single/multi-file, create/modify, path security, stale proposals, approval gating.
Does NOT modify real project files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bolt_core.approval_apply import ApprovalApplyEngine
from bolt_core.write_tool_proposal import (
    OP_CREATE, OP_MODIFY, RISK_LOW,
    STATUS_APPROVED, STATUS_STALE,
    WriteProposal, WriteProposalStore,
)

_DIFF_MOD = ("--- a/src/main.py\n+++ b/src/main.py\n"
             "@@ -1,3 +1,3 @@\n line1\n-line2\n+line2_mod\n line3\n")
_DIFF_NEW = ("--- /dev/null\n+++ b/src/new_file.py\n"
             "@@ -0,0 +1,2 @@\n+#!/usr/bin/env python\n+print('hi')\n")
_DIFF_MULTI = ("--- a/src/a.py\n+++ b/src/a.py\n@@ -1,1 +1,1 @@\n-old_a\n+new_a\n"
               "--- a/src/b.py\n+++ b/src/b.py\n@@ -1,1 +1,1 @@\n-old_b\n+new_b\n")
_DIFF_AONLY = ("--- a/src/a.py\n+++ b/src/a.py\n@@ -1,1 +1,1 @@\n-old\n+new\n")
_DIFF_INJECT = ("--- a/src/main.py\n+++ b/src/main.py\n@@ -1,1 +1,1 @@\n-old\n+new\n"
                "--- a/src/secret.py\n+++ b/src/secret.py\n@@ -0,0 +1,1 @@\n+SECRET=evil\n")


@dataclass(frozen=True)
class PatchApplyEvalCase:
    case_id: str
    description: str
    expected_success: bool
    expected_reason_keyword: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "description": self.description,
                "expected_success": self.expected_success,
                "expected_reason_keyword": self.expected_reason_keyword}


@dataclass(frozen=True)
class PatchApplyEvalResult:
    case_id: str; passed: bool; expected_result: str; actual_result: str
    files_changed: list[str]; safety_notes: str; rollback_hint: str

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "expected_result": self.expected_result, "actual_result": self.actual_result,
                "files_changed": self.files_changed, "safety_notes": self.safety_notes,
                "rollback_hint": self.rollback_hint}


@dataclass
class PatchApplyEvalSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[PatchApplyEvalResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "补丁应用评估在临时目录中运行，不修改真实项目文件。"}


# ── Helpers ──

def _pf(tmp_dir: Path, path: str, content: str) -> None:
    fp = tmp_dir / path; fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")

def _approve(store: WriteProposalStore, pid: str) -> None:
    p = store._proposals.get(pid)
    if p is None: return
    store._proposals[pid] = WriteProposal(
        proposal_id=p.proposal_id, tool_id=p.tool_id, target_files=p.target_files,
        operation_type=p.operation_type, before_summary=p.before_summary,
        after_summary=p.after_summary, diff_preview=p.diff_preview,
        risk_level=p.risk_level, required_permissions=p.required_permissions,
        rollback_hint=p.rollback_hint, chinese_explanation=p.chinese_explanation,
        git_head=p.git_head, status=STATUS_APPROVED, created_at=p.created_at)

def _stale(store: WriteProposalStore, pid: str) -> None:
    p = store._proposals.get(pid)
    if p is None: return
    store._proposals[pid] = WriteProposal(
        proposal_id=p.proposal_id, tool_id=p.tool_id, target_files=p.target_files,
        operation_type=p.operation_type, before_summary=p.before_summary,
        after_summary=p.after_summary, diff_preview=p.diff_preview,
        risk_level=p.risk_level, required_permissions=p.required_permissions,
        rollback_hint=p.rollback_hint, chinese_explanation=p.chinese_explanation,
        git_head="0" * 40, status=STATUS_STALE, created_at=p.created_at)

def _apply(store, engine, case_dir, targets, diff, op_type, approval) -> tuple:
    """Common apply pattern: create proposal, approve, apply, return (success, reason, files)."""
    v = store.create(tool_id="write_file", target_files=targets,
                     operation_type=op_type, diff_preview=diff,
                     risk_level=RISK_LOW, chinese_explanation="eval")
    if not v.valid:
        return (False, "; ".join(v.errors), [])
    pid = v.proposal.proposal_id
    _approve(store, pid)
    result = engine.apply(pid, approval)
    fc = result.audit_record.get("files_changed", []) if result.success else []
    return (result.success, result.reason, fc)


# ── Eval service ──

class PatchApplyEvalService:
    """M112 补丁应用评估服务。"""

    @staticmethod
    def run_all(tmp_dir: Path) -> PatchApplyEvalSummary:
        results = []
        for case in PatchApplyEvalService._cases():
            d = tmp_dir / case.case_id; d.mkdir(parents=True, exist_ok=True)
            results.append(PatchApplyEvalService._run(case, d))
        p = sum(1 for r in results if r.passed)
        return PatchApplyEvalSummary(total_cases=len(results), passed=p,
                                     failed=len(results) - p, results=results)

    @staticmethod
    def _cases() -> list[PatchApplyEvalCase]:
        PC = PatchApplyEvalCase
        return [
            PC("modify_ok", "单文件修改成功", True),
            PC("create_ok", "新建文件成功", True),
            PC("multi_ok", "多文件修改成功", True),
            PC("mismatch", "diff与target不匹配必须失败", False, "缺少对应 diff"),
            PC("inject", "diff注入额外文件必须失败", False, "非目标文件"),
            PC("block_env", ".env路径阻断", False, "secret"),
            PC("block_claude", ".claude路径阻断", False, "禁止写入目录"),
            PC("stale", "过期提案必须失败", False, "过期"),
            PC("agent_self", "agent自我批准必须失败", False, "自我批准"),
            PC("scope_mis", "批准范围不匹配必须失败", False, "不匹配"),
            PC("no_approval", "缺少批准记录必须失败", False, "缺少批准"),
            PC("bypass", "approved=true绕过必须失败", False, "绕过"),
        ]

    @staticmethod
    def _run(case: PatchApplyEvalCase, case_dir: Path) -> PatchApplyEvalResult:
        store = WriteProposalStore(project_dir=str(case_dir))
        engine = ApprovalApplyEngine(store=store, project_dir=str(case_dir))
        ok: bool | None = None; reason = ""; fc: list[str] = []; notes = ""
        cid = case.case_id

        try:
            if cid == "modify_ok":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_MOD, OP_MODIFY, {"actor": "human", "scope": ""})
                if ok: notes = "文件修改正确"
            elif cid == "create_ok":
                ok, reason, fc = _apply(store, engine, case_dir, ["src/new_file.py"],
                                        _DIFF_NEW, OP_CREATE, {"actor": "human", "scope": ""})
            elif cid == "multi_ok":
                _pf(case_dir, "src/a.py", "old_a\n"); _pf(case_dir, "src/b.py", "old_b\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/a.py", "src/b.py"],
                                        _DIFF_MULTI, OP_MODIFY, {"actor": "human", "scope": ""})
                if ok:
                    a_ok = "new_a" in (case_dir / "src/a.py").read_text()
                    b_ok = "new_b" in (case_dir / "src/b.py").read_text()
                    if not (a_ok and b_ok):
                        ok = False; reason = "多文件串改"
                        notes = "文件内容异常"
                    else:
                        notes = "独立修改正确"
            elif cid == "mismatch":
                _pf(case_dir, "src/a.py", "old\n"); _pf(case_dir, "src/b.py", "old_b\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/a.py", "src/b.py"],
                                        _DIFF_AONLY, OP_MODIFY, {"actor": "human", "scope": ""})
                if not ok: notes = f"正确拒绝: {reason}"
            elif cid == "inject":
                _pf(case_dir, "src/main.py", "old\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_INJECT, OP_MODIFY, {"actor": "human", "scope": ""})
                if not ok: notes = f"正确拒绝注入: {reason}"
            elif cid == "block_env":
                v = store.create(tool_id="write_file", target_files=[".env"],
                                 operation_type=OP_MODIFY, diff_preview=_DIFF_MOD,
                                 risk_level=RISK_LOW, chinese_explanation="eval")
                ok = v.valid; reason = "; ".join(v.errors) if not v.valid else ""
                notes = ".env阻断" if not v.valid else "危险:.env未阻断"
            elif cid == "block_claude":
                v = store.create(tool_id="write_file", target_files=[".claude/c.json"],
                                 operation_type=OP_MODIFY, diff_preview=_DIFF_MOD,
                                 risk_level=RISK_LOW, chinese_explanation="eval")
                ok = v.valid; reason = "; ".join(v.errors) if not v.valid else ""
                notes = ".claude/阻断" if not v.valid else "危险:.claude/未阻断"
            elif cid == "stale":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                v = store.create(tool_id="write_file", target_files=["src/main.py"],
                                 operation_type=OP_MODIFY, diff_preview=_DIFF_MOD,
                                 risk_level=RISK_LOW, chinese_explanation="eval")
                if v.valid:
                    pid = v.proposal.proposal_id; _approve(store, pid); _stale(store, pid)
                    result = engine.apply(pid, {"actor": "human", "scope": pid})
                    ok = result.success; reason = result.reason
                else:
                    ok = False; reason = "; ".join(v.errors)
            elif cid == "agent_self":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_MOD, OP_MODIFY, {"actor": "agent", "scope": ""})
            elif cid == "scope_mis":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_MOD, OP_MODIFY, {"actor": "human", "scope": "wrong"})
            elif cid == "no_approval":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_MOD, OP_MODIFY, {})
            elif cid == "bypass":
                _pf(case_dir, "src/main.py", "line1\nline2\nline3\n")
                ok, reason, fc = _apply(store, engine, case_dir, ["src/main.py"],
                                        _DIFF_MOD, OP_MODIFY, {"approved": True})
            if ok is None:
                ok = False; reason = f"未实现: {cid}"
        except Exception as e:
            ok = False; reason = str(e); notes = f"异常: {e}"

        passed = ok == case.expected_success
        if not case.expected_success and not ok:
            kw = case.expected_reason_keyword
            if kw and kw not in reason:
                passed = False
                notes = f"原因不匹配：期望含'{kw}'，实际：'{reason}'"

        return PatchApplyEvalResult(
            case_id=cid, passed=passed,
            expected_result="成功" if case.expected_success else "失败",
            actual_result="成功" if ok else f"失败: {reason}",
            files_changed=fc, safety_notes=notes or ("" if passed else reason),
            rollback_hint="" if case.expected_success else "无需回滚",
        )
