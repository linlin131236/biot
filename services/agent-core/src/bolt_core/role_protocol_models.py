"""Role protocol data models: RoleProtocol, HandoffPackage, ValidationResult,
and the five hard-coded role definitions.

Extracted from role_protocol.py to respect the 300-line size gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Role protocol definition ───────────────────────────────────────────

@dataclass(frozen=True)
class RoleProtocol:
    """Immutable definition of a single multi-agent role."""
    role_id: str
    name_cn: str
    description_cn: str
    responsibilities: list[str]
    allowed_actions: list[str]
    forbidden_actions: list[str]
    can_approve: bool
    can_execute_code: bool
    can_modify_files: bool
    output_requirements: dict  # {field: requirement_cn}
    can_transition_to: list[str]  # role_ids this role may hand off to

    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id, "name_cn": self.name_cn,
            "description_cn": self.description_cn,
            "responsibilities": self.responsibilities,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "can_approve": self.can_approve,
            "can_execute_code": self.can_execute_code,
            "can_modify_files": self.can_modify_files,
            "output_requirements": self.output_requirements,
            "can_transition_to": self.can_transition_to,
        }


@dataclass(frozen=True)
class HandoffPackage:
    """Structured handoff between two roles. Read-only; never auto-executed."""
    from_role: str
    to_role: str
    task_id: str
    summary_cn: str
    evidence_refs: list[str]
    source_refs: list[str]
    warnings: list[str]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "from_role": self.from_role, "to_role": self.to_role,
            "task_id": self.task_id, "summary_cn": self.summary_cn,
            "evidence_refs": self.evidence_refs,
            "source_refs": self.source_refs, "warnings": self.warnings,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Result of a role validation check."""
    valid: bool
    message_cn: str
    details: list[str] = field(default_factory=list)
    blocked: bool = False  # True = hard block, must not proceed

    def to_dict(self) -> dict:
        return {
            "valid": self.valid, "message_cn": self.message_cn,
            "details": self.details, "blocked": self.blocked,
        }


# ── Five role definitions ──────────────────────────────────────────────

_PLANNER = RoleProtocol(
    role_id="planner", name_cn="规划者",
    description_cn="负责任务分解、验收标准定义和角色分配。不写代码，不执行命令。",
    responsibilities=[
        "将需求拆分为可验证的子任务", "定义验收标准和完成条件",
        "将子任务分配给合适的角色（Builder/Researcher/Reviewer）",
        "评估任务风险等级", "维护任务依赖关系",
    ],
    allowed_actions=[
        "读取项目文档和代码", "查阅决策记忆和失败记忆",
        "创建子任务分配", "更新任务状态", "输出任务计划（结构化）",
    ],
    forbidden_actions=[
        "编写或修改任何代码文件", "执行任何 shell 命令",
        "批准任何实现结果", "直接操作文件系统（写）",
        "自我批准自己的计划输出",
    ],
    can_approve=False, can_execute_code=False, can_modify_files=False,
    output_requirements={
        "task_breakdown": "任务拆解清单，每个子任务有标题、描述、验收标准",
        "risk_assessment": "风险评估（low/medium/high/critical）",
        "assignment": "每个子任务分配的角色",
        "source_refs": "引用的项目文档和决策记忆路径",
    },
    can_transition_to=["builder", "researcher"],
)

_RESEARCHER = RoleProtocol(
    role_id="researcher", name_cn="研究员",
    description_cn="只读调研角色。阅读指定资料和代码，输出摘要和 source_refs。不能实现、不能改文件。",
    responsibilities=[
        "读取指定的项目文档和参考资料", "阅读相关代码模块",
        "提炼架构原则和关键发现", "输出结构化摘要和 source_refs",
        "标注风险和建议",
    ],
    allowed_actions=[
        "读取项目文档、代码、决策记忆",
        "读取 BinCloud 参考资料（限 2-4 篇）",
        "读取失败记忆和项目画像", "输出研究摘要",
    ],
    forbidden_actions=[
        "编写或修改任何代码文件", "执行任何 shell 命令",
        "生成 patch 或 diff", "批准任何结果",
        "爬取整个知识库（每次限 2-4 篇相关材料）",
        "修改文档或配置文件",
    ],
    can_approve=False, can_execute_code=False, can_modify_files=False,
    output_requirements={
        "summary_cn": "中文摘要，包含采用原则和风险",
        "source_refs": "所有引用的文档路径和段落",
        "findings": "关键发现列表", "risk_notes": "风险提示（如有）",
    },
    can_transition_to=["planner"],
)

_BUILDER = RoleProtocol(
    role_id="builder", name_cn="构建者",
    description_cn="负责代码实现、测试编写和变更提交。不能自我批准，不能审查自己的工作。",
    responsibilities=[
        "根据 Planner 的任务分配实现代码", "编写 targeted tests",
        "提交代码变更", "修复 Reviewer 发现的问题", "更新相关文档",
    ],
    allowed_actions=[
        "读写代码文件", "执行测试命令", "提交 git commit",
        "读取项目文档作为参考", "读取 Reviewer 的审查结果",
    ],
    forbidden_actions=[
        "批准自己的工作（self-approve）", "审查自己的代码输出",
        "绕过 PermissionGate 执行危险命令",
        "自动 push/release/tag/delete",
        "修改 Reviewer 的审查结论", "修改 Planner 的任务计划",
    ],
    can_approve=False, can_execute_code=True, can_modify_files=True,
    output_requirements={
        "code_changes": "代码变更（通过 git diff 可追溯）",
        "tests": "targeted tests 全部通过",
        "evidence_refs": "测试结果、lint 结果路径",
        "source_refs": "引用的需求和计划文档",
    },
    can_transition_to=["reviewer"],
)

_REVIEWER = RoleProtocol(
    role_id="reviewer", name_cn="审查者",
    description_cn="独立审查角色。审查 Builder 的输出，找 P1/P2 问题。不能实现自己的审查发现，不能审查自己的工作。",
    responsibilities=[
        "审查 Builder 的代码和测试输出",
        "从多角度评估代码质量（复用、简化、效率、层次）",
        "分类问题为 P1/P2/P3", "输出结构化审查报告", "决定是否批准变更",
    ],
    allowed_actions=[
        "读取代码和测试文件", "读取项目文档和决策记忆",
        "读取失败记忆（检查已知风险）", "输出审查报告",
        "批准他人工作（approved/changes_requested/blocked）",
    ],
    forbidden_actions=[
        "修改 Builder 的代码", "实现自己的审查发现",
        "批准自己的工作", "审查与 Builder 是同一上下文的工作",
        "执行任何代码变更命令", "绕过质量门禁批准",
    ],
    can_approve=True, can_execute_code=False, can_modify_files=False,
    output_requirements={
        "findings": "发现的问题列表（P1/P2/P3）",
        "evidence": "每个发现对应的代码位置和理由",
        "tests_status": "测试结果评估",
        "residual_risks": "残留风险标注",
        "verdict": "approved / changes_requested / blocked",
    },
    can_transition_to=["builder"],
)

_SKILL_LEARNER = RoleProtocol(
    role_id="skill_learner", name_cn="技能学习者",
    description_cn="分析流程缺陷，提出技能/流程/文档改进建议。只提案，不改业务代码。必须等用户审批。",
    responsibilities=[
        "收集同类失败模式（>= 2 次触发）",
        "分析流程和技能文档的改进空间",
        "提出 A/B/C 改进方案",
        "标注改进目标类型（workflow_doc/skill_doc/review_policy）",
    ],
    allowed_actions=[
        "读取失败记忆和决策记忆", "读取技能文档和流程文档",
        "读取代码（了解流程，不改代码）", "输出改进提案",
    ],
    forbidden_actions=[
        "修改任何业务代码", "直接修改技能文件或流程文档",
        "执行代码或命令", "未经用户审批应用任何改动",
        "批准任何结果", "修改项目配置文件",
    ],
    can_approve=False, can_execute_code=False, can_modify_files=False,
    output_requirements={
        "proposal_options": "A/B/C 方案，每个方案有描述和影响评估",
        "evidence": "触发提案的失败模式证据",
        "source_refs": "引用的失败记忆和相关文档",
        "target_type": "workflow_doc / skill_doc / review_policy / unknown",
        "requires_father_approval": "必须为 true",
    },
    can_transition_to=["planner"],
)

_ROLES: dict[str, RoleProtocol] = {
    "planner": _PLANNER, "researcher": _RESEARCHER,
    "builder": _BUILDER, "reviewer": _REVIEWER,
    "skill_learner": _SKILL_LEARNER,
}

_ROLE_ORDER = ["planner", "researcher", "builder", "reviewer", "skill_learner"]

_BUILDER_SELF_APPROVAL_MESSAGE = (
    "构建者不能批准自己的工作。审查必须由独立的审查者角色完成。"
    "请将工作移交给审查者角色进行评估。"
)
_REVIEWER_SELF_IMPLEMENT_MESSAGE = (
    "审查者不能实现自己的审查发现。审查发现应返回给构建者进行修复。"
    "如果审查者发现了问题，请将审查报告交给构建者处理。"
)
