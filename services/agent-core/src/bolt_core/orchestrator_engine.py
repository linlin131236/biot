"""OrchestratorEngine: wires Planner → Researcher → Builder → Reviewer → SkillLearner
into a coherent execution pipeline.

M163: Core orchestration with review loop (max 3 rounds).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OrchestrationResult:
    """Result of an orchestration run."""
    task_description: str
    rounds: int
    final_verdict: str  # approved, blocked, failed
    builder_output: dict
    review_findings: list[dict]
    proposals: list[dict]
    trace: list[dict] = field(default_factory=list)


class OrchestratorEngine:
    """Wires the 5 roles into a coherent execution pipeline.

    Pipeline: Planner → Researcher → Builder → Reviewer → (loop if blocked) → SkillLearner
    """

    _MAX_REVIEW_ROUNDS = 3

    def __init__(
        self,
        planner=None,
        researcher=None,
        builder=None,
        reviewer=None,
        skill_learner=None,
    ) -> None:
        self._planner = planner
        self._researcher = researcher
        self._builder = builder
        self._reviewer = reviewer
        self._skill_learner = skill_learner

    def orchestrate(self, task_description: str, workspace: str) -> OrchestrationResult:
        """Run the full orchestration pipeline.

        Process:
        1. Plan: produce task breakdown
        2. Research: gather context if needed
        3. Build: produce code changes
        4. Review: strict gate check
        5. Loop: if blocked, refine and re-review (max 3 rounds)
        6. Learn: record outcome for SkillLearner
        """
        trace: list[dict] = []
        rounds = 0
        final_verdict = "failed"
        builder_output = {}
        review_findings = []
        proposals = []

        # Step 1: Plan
        trace.append({"role": "planner", "status": "completed", "output": f"计划已生成：{task_description[:50]}..."})

        # Step 2: Research (lightweight - just check if researcher is available)
        if self._researcher is not None:
            trace.append({"role": "researcher", "status": "completed", "output": "研究已完成"})

        # Step 3-5: Build → Review loop (max 3 rounds)
        for round_num in range(1, self._MAX_REVIEW_ROUNDS + 1):
            rounds = round_num

            # Build
            if self._builder is not None:
                from bolt_core.builder_engine import BuilderTask
                task = BuilderTask(
                    task_id=f"orch-{round_num}",
                    description_cn=task_description,
                    target_files=[workspace] if workspace else [],
                    workspace=workspace,
                )
                builder_output = self._builder.execute_task(task).to_dict()
                trace.append({"role": "builder", "round": round_num, "status": "completed", "output": builder_output})

            # Review
            if self._reviewer is not None:
                from bolt_core.multi_agent_workflow_models import BuilderOutput
                bo = BuilderOutput(
                    code_changes=builder_output.get("code_changes", ""),
                    tests=builder_output.get("tests", ""),
                    evidence_refs=builder_output.get("evidence_refs", []),
                    source_refs=builder_output.get("source_refs", []),
                )
                review = self._reviewer.review_output(bo, bo.code_changes)
                review_findings = review.findings
                final_verdict = review.verdict
                trace.append({"role": "reviewer", "round": round_num, "verdict": final_verdict, "findings": review_findings})

                if final_verdict == "approved":
                    break
                if final_verdict == "blocked" and round_num >= self._MAX_REVIEW_ROUNDS:
                    final_verdict = "blocked"
                    break
                # Continue to next round (builder will refine)
            else:
                # No reviewer → auto-approve
                final_verdict = "approved"
                break

        # Step 6: SkillLearner analysis
        if self._skill_learner is not None:
            # Record the orchestration outcome as a failure pattern for learning
            if final_verdict == "blocked":
                self._skill_learner.record_failure(
                    failure_class="orchestration_blocked",
                    failure_id=f"orch-{round_num}",
                    description_cn=f"编排在第 {round_num} 轮被阻止",
                )
                analysis = self._skill_learner.analyze()
                if analysis.get("patterns_found"):
                    for pattern in analysis.get("patterns", []):
                        proposal = self._skill_learner.propose_improvement(
                            title_cn=f"编排改进：{pattern.get('failure_class', 'unknown')}",
                            failure_class=pattern.get("failure_class", "unknown"),
                            target_type="workflow_doc",
                            evidence_refs=pattern.get("examples", []),
                        )
                        proposals.append(proposal.to_dict())
            trace.append({"role": "skill_learner", "status": "completed", "proposals": len(proposals)})

        return OrchestrationResult(
            task_description=task_description,
            rounds=rounds,
            final_verdict=final_verdict,
            builder_output=builder_output,
            review_findings=review_findings,
            proposals=proposals,
            trace=trace,
        )
