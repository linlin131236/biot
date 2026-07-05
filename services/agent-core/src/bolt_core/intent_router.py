from bolt_core.perception_types import IntentClassification

RULES = [
    ("debug", ["bug", "fix", "error", "failed", "失败", "报错", "修复", "调试"]),
    ("ui_improvement", ["ui", "页面", "界面", "样式", "视觉", "优化", "redesign"]),
    ("run_command", ["run", "execute", "运行", "执行", "pnpm", "pytest", "build"]),
    ("review", ["review", "审查", "评审", "检查代码"]),
    ("code_change", ["implement", "add", "change", "refactor", "实现", "新增", "修改", "重构"]),
    ("planning", ["plan", "roadmap", "milestone", "规划", "计划", "路线图"]),
]
QUESTION_WORDS = ["what", "why", "how", "explain", "解释", "说明", "是什么", "为什么"]


def classify_intent(goal: str) -> IntentClassification:
    text = goal.lower()
    for category, words in RULES:
        matches = [word for word in words if word in text]
        if matches:
            return IntentClassification(category, 0.8, matches)
    matches = [word for word in QUESTION_WORDS if word in text]
    if matches or goal.strip().endswith("?") or goal.strip().endswith("？"):
        return IntentClassification("question", 0.7, matches)
    return IntentClassification("question", 0.4, [])
