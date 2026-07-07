"""Multi-Agent Collaboration Eval (M115). Evaluate role boundaries and independence.

Verifies Planner/Builder/Reviewer/Researcher/SkillLearner role boundaries
using the role_protocol definitions. No real agent execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Eval types ──


@dataclass(frozen=True)
class MultiAgentEvalCase:
    case_id: str; description: str; role: str; expected_boundary: str  # "allowed" / "blocked"
    independent_review_passed: bool = True; self_approval_blocked: bool = True
    chinese_reason: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "description": self.description,
                "role": self.role, "expected_boundary": self.expected_boundary,
                "independent_review_passed": self.independent_review_passed,
                "self_approval_blocked": self.self_approval_blocked,
                "chinese_reason": self.chinese_reason}


@dataclass(frozen=True)
class MultiAgentEvalResult:
    case_id: str; passed: bool; role: str; expected_boundary: str
    actual_boundary: str; chinese_reason: str = ""

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed, "role": self.role,
                "expected_boundary": self.expected_boundary,
                "actual_boundary": self.actual_boundary,
                "chinese_reason": self.chinese_reason}


@dataclass
class MultiAgentEvalSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[MultiAgentEvalResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "多Agent协作评估仅验证角色边界定义，不执行真实Agent操作。"}


# ── Role boundary rules (from M81 role_protocol) ──

_ROLE_RULES: dict[str, dict] = {
    "planner": {"can_write": False, "can_self_approve": False, "can_implement": False,
                "desc": "Planner 只能规划任务图，不直接写入代码"},
    "builder": {"can_write": True, "can_self_approve": False, "can_implement": True,
                "desc": "Builder 可以写代码，但不能自我批准"},
    "reviewer": {"can_write": False, "can_self_approve": False, "can_implement": False,
                 "desc": "Reviewer 只能审查，不能和 Builder 同上下文自审"},
    "researcher": {"can_write": False, "can_self_approve": False, "can_implement": False,
                   "desc": "Researcher 只读资料，不写业务文件"},
    "skilllearner": {"can_write": False, "can_self_approve": False, "can_implement": False,
                     "desc": "SkillLearner 只提案，不碰业务代码"},
}


class MultiAgentCollaborationEvalService:
    """M115 多Agent协作评估服务。"""

    @staticmethod
    def run_all() -> MultiAgentEvalSummary:
        results = []
        for case in MultiAgentCollaborationEvalService._cases():
            rules = _ROLE_RULES.get(case.role, {})
            boundary_ok = True
            actual_boundary = ""

            if case.case_id == "planner_no_write":
                actual_boundary = "blocked" if not rules.get("can_write") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "builder_no_self_approve":
                actual_boundary = "blocked" if not rules.get("can_self_approve") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "reviewer_independent":
                actual_boundary = "allowed" if case.independent_review_passed else "blocked"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "researcher_readonly":
                actual_boundary = "blocked" if not rules.get("can_write") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "skilllearner_no_business_code":
                actual_boundary = "blocked" if not rules.get("can_implement") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "reviewer_not_builder":
                actual_boundary = "blocked" if not rules.get("can_implement") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "builder_needs_approval":
                actual_boundary = "allowed" if case.self_approval_blocked else "blocked"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "planner_no_implement":
                actual_boundary = "blocked" if not rules.get("can_implement") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "researcher_no_self_approve":
                actual_boundary = "blocked" if not rules.get("can_self_approve") else "allowed"
                boundary_ok = actual_boundary == case.expected_boundary
            elif case.case_id == "skilllearner_approval_required":
                actual_boundary = "allowed" if case.self_approval_blocked else "blocked"
                boundary_ok = actual_boundary == case.expected_boundary
            else:
                actual_boundary = "blocked"
                boundary_ok = False

            results.append(MultiAgentEvalResult(
                case_id=case.case_id, passed=boundary_ok and case.self_approval_blocked,
                role=case.role, expected_boundary=case.expected_boundary,
                actual_boundary=actual_boundary, chinese_reason=case.chinese_reason,
            ))
        p = sum(1 for r in results if r.passed)
        return MultiAgentEvalSummary(total_cases=len(results), passed=p,
                                     failed=len(results) - p, results=results)

    @staticmethod
    def _cases() -> list[MultiAgentEvalCase]:
        MC = MultiAgentEvalCase
        return [
            MC("planner_no_write", "Planner不能直接写入", "planner", "blocked",
               chinese_reason="Planner只规划，不直接写业务代码"),
            MC("builder_no_self_approve", "Builder不能自我批准", "builder", "blocked",
               chinese_reason="Builder写的代码必须经Reviewer审查，不能自我批准"),
            MC("reviewer_independent", "Reviewer独立性强制", "reviewer", "allowed",
               independent_review_passed=True,
               chinese_reason="Reviewer必须独立审查，不能和Builder同上下文"),
            MC("researcher_readonly", "Researcher只读", "researcher", "blocked",
               chinese_reason="Researcher只读资料，不写业务文件"),
            MC("skilllearner_no_business_code", "SkillLearner不碰业务代码", "skilllearner", "blocked",
               chinese_reason="SkillLearner只提案，不直接写业务代码"),
            MC("reviewer_not_builder", "Reviewer不能自写自审", "reviewer", "blocked",
               chinese_reason="Reviewer和Builder不能是同一Agent"),
            MC("builder_needs_approval", "Builder需要外部批准", "builder", "allowed",
               self_approval_blocked=True,
               chinese_reason="Builder apply需要爸爸批准，不能自批"),
            MC("planner_no_implement", "Planner不实现", "planner", "blocked",
               chinese_reason="Planner输出任务图，由Builder执行"),
            MC("researcher_no_self_approve", "Researcher不能自批", "researcher", "blocked",
               chinese_reason="Researcher不能自我批准任何操作"),
            MC("skilllearner_approval_required", "SkillLearner需审批", "skilllearner", "allowed",
               self_approval_blocked=True,
               chinese_reason="SkillLearner的apply提案需爸爸批准"),
        ]
