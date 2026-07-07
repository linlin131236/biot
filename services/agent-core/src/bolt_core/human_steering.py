"""Human Steering Service. Classifies user intent and generates safe steering results.

Design principles (from AgentHarness 20-layer guide, s03-s04):
- Permission gate: whitelist → rules → user confirmation. Steering never bypasses this.
- Hooks pattern: steering hangs on the agent loop, doesn't invade it.
- All results recorded as verifiable evidence (conversation store + trace log).

Safety invariants:
- NEVER calls approve_permission
- NEVER executes shell
- NEVER writes files
- NEVER directly executes dangerous actions
- change_goal / abort → pending only, requires human confirmation
- pause → delegates to M66 PauseResumeService
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class SteeringIntent(str, Enum):
    """Classified user steering intent. Six categories."""
    CONTINUE = "continue"
    PAUSE = "pause"
    CHANGE_GOAL = "change_goal"
    REQUEST_REVIEW = "request_review"
    ABORT = "abort"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SteeringResult:
    """Safe steering result. Carries classification, explanation, and action plan.

    NEVER contains executable instructions. All side-effect intents go to pending.
    """
    intent: str
    intent_label: str  # 中文标签
    explanation: str  # 中文解释
    requires_human_confirmation: bool
    action_taken: str  # 中文描述已执行动作
    pending_actions: list[str] = field(default_factory=list)
    evidence_ref: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "intent_label": self.intent_label,
            "explanation": self.explanation,
            "requires_human_confirmation": self.requires_human_confirmation,
            "action_taken": self.action_taken,
            "pending_actions": self.pending_actions,
            "evidence_ref": self.evidence_ref,
            "timestamp": self.timestamp,
        }


# ── Classification rules ──────────────────────────────────────────────
# Ordered from most specific → least specific. First match wins.
_INTENT_RULES: list[tuple[SteeringIntent, list[str], str]] = [
    (SteeringIntent.ABORT, [
        "取消", "终止", "放弃", "abort", "cancel", "kill", "退出",
    ], "中止"),
    (SteeringIntent.PAUSE, [
        "暂停", "pause", "停一下", "等一下", "stop", "wait", "等等",
        "先停", "停", "暂缓",
    ], "暂停"),
    (SteeringIntent.CHANGE_GOAL, [
        "改成", "改为", "修改目标", "换一个", "change goal", "变更目标",
        "调整目标", "换个", "不做这个", "改做",
    ], "变更目标"),
    (SteeringIntent.REQUEST_REVIEW, [
        "检查", "复查", "review", "看看", "审视", "审核", "审阅",
        "帮我看看", "看一下", "查一下",
    ], "请求审查"),
    (SteeringIntent.CONTINUE, [
        "继续", "go on", "resume", "proceed", "接着", "往下",
        "下一步", "ok", "好的", "可以", "行",
    ], "继续"),
]


def _classify(content: str) -> tuple[SteeringIntent, str]:
    """Classify user input into a steering intent.

    Returns (intent, matched_label). Unknown intent returns (UNKNOWN, "无法识别").
    """
    lower = content.lower().strip()
    if not lower:
        return SteeringIntent.UNKNOWN, "无法识别"
    for intent, keywords, label in _INTENT_RULES:
        for kw in keywords:
            if kw in lower:
                return intent, label
    return SteeringIntent.UNKNOWN, "无法识别"


# ── Service ───────────────────────────────────────────────────────────

class HumanSteeringService:
    """Classifies and processes human steering input safely.

    Does NOT execute dangerous actions. Does NOT approve permissions.
    Integrates with M66 PauseResumeService for pause steering.
    """

    def __init__(self, pause_service=None, record_evidence: Callable | None = None) -> None:
        self._pause_service = pause_service  # PauseResumeService instance (optional)
        self._record_evidence = record_evidence  # Callable(run_id, result) for evidence

    def process(self, run_id: str, content: str,
                current_node_id: str | None = None,
                current_status: str | None = None) -> SteeringResult:
        """Process a user steering input.

        Args:
            run_id: The run being steered.
            content: Raw user input text.
            current_node_id: Optional node ID for pause steering (M66 integration).
            current_status: Optional node status for pause steering (M66 integration).

        Returns:
            SteeringResult with classification, explanation, and safe action plan.
        """
        intent, label = _classify(content)
        evidence_ref = f"steering_{uuid.uuid4().hex[:12]}"
        now = time.time()

        if intent == SteeringIntent.CONTINUE:
            result = SteeringResult(
                intent="continue",
                intent_label="继续",
                explanation=f"收到继续指令。当前任务将继续执行，不受 steering 影响。原始输入：{content[:80]}",
                requires_human_confirmation=False,
                action_taken="已记录继续意图，任务流程不变。",
                pending_actions=[],
                evidence_ref=evidence_ref,
                timestamp=now,
            )

        elif intent == SteeringIntent.PAUSE:
            result = self._handle_pause(run_id, content, evidence_ref, now,
                                        current_node_id, current_status)

        elif intent == SteeringIntent.CHANGE_GOAL:
            pending = [f"变更目标请求已记录。原始输入：{content[:200]}。需人工确认后由 Planner 重新规划。"]
            result = SteeringResult(
                intent="change_goal",
                intent_label="变更目标",
                explanation=f"收到目标变更请求。此操作涉及任务范围变更，需要人工二次确认后才能执行。原始输入：{content[:80]}",
                requires_human_confirmation=True,
                action_taken="已记录变更目标请求（pending 状态），未修改任何目标。",
                pending_actions=pending,
                evidence_ref=evidence_ref,
                timestamp=now,
            )

        elif intent == SteeringIntent.REQUEST_REVIEW:
            result = SteeringResult(
                intent="request_review",
                intent_label="请求审查",
                explanation=f"收到审查请求。将在当前步骤完成后暂停并请求人工审查。原始输入：{content[:80]}",
                requires_human_confirmation=False,
                action_taken="已记录审查请求，将在合适时机触发审查门。",
                pending_actions=[],
                evidence_ref=evidence_ref,
                timestamp=now,
            )

        elif intent == SteeringIntent.ABORT:
            pending = [f"中止请求已记录。原始输入：{content[:200]}。需人工二次确认后执行中止操作。"]
            result = SteeringResult(
                intent="abort",
                intent_label="中止",
                explanation=f"收到中止请求。中止操作不可逆，需要人工二次确认。原始输入：{content[:80]}",
                requires_human_confirmation=True,
                action_taken="已记录中止请求（pending 状态），未终止任何进程。",
                pending_actions=pending,
                evidence_ref=evidence_ref,
                timestamp=now,
            )

        else:  # UNKNOWN
            result = SteeringResult(
                intent="unknown",
                intent_label="无法识别",
                explanation=(
                    f"无法识别您的指令意图。请使用更明确的指令，例如："
                    f"「继续」「暂停」「修改目标」「检查一下」「取消任务」。"
                    f"原始输入：{content[:80]}"
                ),
                requires_human_confirmation=False,
                action_taken="未执行任何操作。请重新输入明确指令。",
                pending_actions=[],
                evidence_ref=evidence_ref,
                timestamp=now,
            )

        # Record evidence if callback provided
        if self._record_evidence is not None:
            try:
                self._record_evidence(run_id, result)
            except Exception:
                pass  # evidence recording failure should not block steering

        return result

    def _handle_pause(self, run_id: str, content: str, evidence_ref: str,
                      now: float, node_id: str | None,
                      current_status: str | None) -> SteeringResult:
        """Handle pause steering via M66 PauseResumeService when possible."""
        # Try M66 integration
        if self._pause_service is not None and node_id and current_status:
            try:
                pause_result = self._pause_service.pause(
                    node_id, current_status,
                    reason=f"用户 steering 暂停：{content[:200]}",
                    evidence_refs=[evidence_ref],
                )
                return SteeringResult(
                    intent="pause",
                    intent_label="暂停",
                    explanation=(
                        f"已通过 M66 暂停机制暂停节点 '{node_id}'。"
                        f"快照 ID：{pause_result['snapshot']['snapshot_id']}。"
                        f"恢复时需重新验证权限。原始输入：{content[:80]}"
                    ),
                    requires_human_confirmation=False,
                    action_taken=f"节点 '{node_id}' 已暂停，快照已保存。{pause_result.get('warning', '')}",
                    pending_actions=[
                        f"恢复节点 '{node_id}' 时需通过 PermissionGate 重新验证权限。"
                    ],
                    evidence_ref=evidence_ref,
                    timestamp=now,
                )
            except ValueError as e:
                # M66 pause rejected (wrong state, already paused, etc.)
                return SteeringResult(
                    intent="pause",
                    intent_label="暂停",
                    explanation=f"暂停请求被 M66 暂停机制拒绝：{e}。原始输入：{content[:80]}",
                    requires_human_confirmation=False,
                    action_taken=f"暂停未执行。原因：{e}",
                    pending_actions=[],
                    evidence_ref=evidence_ref,
                    timestamp=now,
                )

        # Fallback: no M66 integration available
        return SteeringResult(
            intent="pause",
            intent_label="暂停",
            explanation=f"收到暂停指令。暂停请求已记录。原始输入：{content[:80]}",
            requires_human_confirmation=False,
            action_taken="已记录暂停意图。如已接入 M66 暂停机制，将由 M66 处理。",
            pending_actions=[],
            evidence_ref=evidence_ref,
            timestamp=now,
        )
