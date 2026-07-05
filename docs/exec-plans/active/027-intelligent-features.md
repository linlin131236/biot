# Exec Plan 027 - Intelligent Agent Features

## Goal

Add the most impactful "smart" features from Codex and Claude Code's 2026 updates: plan mode, auto-compact, hooks system, agent templates, and multi-repo support. These make Bolt not just functional but genuinely intelligent.

## Why Now

After Plans 019-026, Bolt has real LLM, tools, memory, MoA, and multi-provider. But it's still a reactive command executor. The features in this plan make it proactive, self-managing, and team-ready.

## Scope

### 1. Plan Mode (Codex `/plan` inspired)

Before making any changes, Bolt can switch to "plan only" mode where it reads files, analyzes, and produces a step-by-step plan without executing any writes.

New file: `services/agent-core/src/bolt_core/plan_mode.py`

```python
class PlanMode:
    """Read-only analysis mode. No writes, no shell commands. Just analysis + plan."""
    
    def generate_plan(self, goal: str, workspace: str, context: dict) -> Plan:
        # 1. Read relevant files (file.read + files.search only)
        # 2. Analyze current state
        # 3. Generate step-by-step plan with:
        #    - What to change
        #    - Why
        #    - Expected outcome
        #    - Risk assessment
        # Return Plan object (no execution)
        pass

@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    estimated_risk: str  # "low" / "medium" / "high"
    files_affected: list[str]

@dataclass
class PlanStep:
    description: str
    tool: str           # which tool will be used
    reason: str         # why this step is needed
    rollback: str       # how to undo if something goes wrong
```

Plan mode tools (read-only subset):
- `file.read` ✅
- `files.search` ✅
- `web.search` ✅
- `web.extract` ✅
- `file.write` ❌ (blocked)
- `file.patch` ❌ (blocked)
- `shell.execute` ❌ (blocked)
- `terminal.spawn` ❌ (blocked)

User can approve the plan → Bolt switches to execution mode and follows the plan step by step.

### 2. Auto-Compact (Codex `/compact` inspired)

Automatically compress conversation context when approaching token limits, preserving key decisions and instructions.

New file: `services/agent-core/src/bolt_core/auto_compact.py`

```python
class AutoCompact:
    def __init__(self, threshold: float = 0.8):
        # threshold: compact when context usage exceeds 80% of budget
        self.threshold = threshold
    
    def should_compact(self, messages: list[ConversationMessage], budget: int) -> bool:
        estimated_tokens = sum(len(m.content) for m in messages) // 4
        return estimated_tokens > budget * self.threshold
    
    def compact(self, messages: list[ConversationMessage], gateway) -> list[ConversationMessage]:
        # 1. Keep system prompt (always)
        # 2. Keep last 10 messages (recent context)
        # 3. Summarize older messages via LLM call
        # 4. Return compressed message list
        pass
```

Trigger: before each LLM call, check if compaction needed. If yes, compact automatically. Log compaction event in trace.

### 3. Hooks System (Claude Code inspired)

User-defined scripts that run before/after key agent events. Enables custom validation, notification, and workflow automation.

New file: `services/agent-core/src/bolt_core/hooks.py`

```python
@dataclass
class Hook:
    event: str         # "pre_write", "post_write", "pre_shell", "post_step", "subagent_complete"
    command: str       # shell command to run
    blocking: bool     # if True, agent waits for hook to complete; if False, async
    
class HookRunner:
    def __init__(self, hooks: list[Hook]):
        self.hooks = hooks
    
    def run(self, event: str, context: dict) -> HookResult:
        # Find matching hooks
        # Execute command with context as env vars
        # Return pass/fail + output
        pass
```

Hook events:

| Event | When | Context available |
|---|---|---|
| `pre_write` | Before file write/patch | path, proposed_content, diff |
| `post_write` | After file write/patch | path, status |
| `pre_shell` | Before shell command | command, workdir |
| `post_step` | After each agent step | step_number, tool_used, status |
| `subagent_complete` | Sub-agent finishes | task_id, summary |
| `budget_exceeded` | Cost budget hit | total_cost, budget |
| `compact` | Context compacted | tokens_before, tokens_after |

Config in `~/.bolt/hooks.yaml`:

```yaml
hooks:
  - event: pre_write
    command: "python scripts/validate-imports.py $BOLT_FILE_PATH"
    blocking: true
  - event: post_step
    command: "notify-send 'Bolt step done' '$BOLT_TOOL used'"
    blocking: false
```

### 4. Agent Templates (Claude Code inspired)

Pre-defined, reusable agent configurations with role, model, permissions, and budget.

New file: `services/agent-core/src/bolt_core/agent_templates.py`

```python
@dataclass
class AgentTemplate:
    name: str              # "code-reviewer"
    description: str
    model: str             # "zyloo/claude-sonnet-5"
    system_prompt: str     # role-specific instructions
    allowed_tools: list[str]
    denied_tools: list[str]
    can_write: bool
    budget: float          # max cost in $
    max_tokens: int
    
class TemplateStore:
    def __init__(self, template_dir: str = "~/.bolt/templates"):
        # Scan {template_dir}/*.yaml
        pass
    
    def load(self, name: str) -> AgentTemplate
    def list(self) -> list[AgentTemplate]
    def save(self, template: AgentTemplate) -> None
```

Built-in templates (ship with Bolt):

| Template | Role | Model | Tools | Write | Budget |
|---|---|---|---|---|---|
| `code-reviewer` | Review code for bugs, style, security | Strong model | read, search | No | $0.25 |
| `bug-fixer` | Systematic debugging + fix | Strong model | all | Yes | $1.00 |
| `test-writer` | Write tests for existing code | Mid model | read, search, write, patch | Yes | $0.50 |
| `researcher` | Search docs, analyze options | Cheap model | read, search, web | No | $0.25 |
| `planner` | Analyze + plan, no execution | Cheap model | read, search, web | No | $0.15 |

Template YAML example (`~/.bolt/templates/code-reviewer.yaml`):

```yaml
name: code-reviewer
description: "Reviews code for style, bugs, and security issues"
model: zyloo/claude-sonnet-5
system_prompt: |
  You are a senior code reviewer. Analyze the code for:
  1. Logic errors and potential bugs
  2. Security vulnerabilities
  3. Performance issues
  4. Style and readability
  Output a prioritized list of findings with severity levels.
allowed_tools: [file.read, files.search, web.search]
denied_tools: [file.write, file.patch, shell.execute]
can_write: false
budget: 0.25
max_tokens: 30000
```

### 5. Multi-Repo Support (Claude Code inspired)

Sub-agents can operate across multiple local repositories in one session.

Update file: `services/agent-core/src/bolt_core/sub_agent.py`

```python
@dataclass
class SubAgentTask:
    # ... existing fields ...
    repos: list[str]    # NEW: multiple workspace paths
```

Agent config:

```yaml
agents:
  - role: dependency_updater
    repos:
      - "D:/projects/frontend"
      - "D:/projects/backend"
      - "D:/projects/shared-libs"
    tasks:
      - "Update axios to 1.8.0 across all repos"
```

Permission scoping: sub-agent's `allow_paths` is the union of all listed repos.

### 6. Scoped Permissions for Sub-Agents (Claude Code inspired)

Sub-agents get fine-grained permission scoping: path restrictions, tool restrictions, write capability.

Update file: `services/agent-core/src/bolt_core/permission_gate.py`

```python
class ScopedPermissionGate(PermissionGate):
    def __init__(self, workspace: str, scope: PermissionScope):
        super().__init__(workspace)
        self.scope = scope
    
    def evaluate(self, request: ToolRequest) -> PermissionDecision:
        # Check scope.allow_paths — deny if path not in allowed set
        # Check scope.deny_tools — deny if tool is blocked
        # Check scope.can_write — deny write operations if false
        # Then fall through to normal risk classification
        pass

@dataclass
class PermissionScope:
    allow_paths: list[str]   # ["${PROJECT_ROOT}/src"]
    deny_tools: list[str]    # ["shell.execute", "file.delete"]
    can_write: bool          # false = read-only agent
```

### 7. Agent Checkpointing Enhancement

Building on Plan 026's basic checkpointing, add:
- File conflict detection on resume (diff checkpointed state vs current disk state)
- Selective checkpoint (only save specific sub-agents, not entire tree)
- Auto-checkpoint before risky operations (auto-checkpoint before `shell.execute` with confirm-level commands)

## Safety Boundary

- Plan mode is strictly read-only. No writes can happen in plan mode.
- Auto-compact may lose detail — acceptable tradeoff for context management.
- Hooks run as subprocess commands. If a blocking hook fails (non-zero exit), the agent step is aborted (safe default).
- Templates are user-defined. Built-in templates are suggestions, not enforcement.
- Multi-repo agents with write access can modify across repos — user must approve each write via PermissionGate.
- Scoped permissions cannot expand beyond the parent agent's scope (principle of least privilege).

## Verification

1. All existing tests pass.
2. New tests:
   - `test_plan_mode_readonly_no_writes`
   - `test_plan_mode_generates_step_by_step_plan`
   - `test_auto_compact_triggers_at_threshold`
   - `test_auto_compact_preserves_system_prompt`
   - `test_hook_runner_blocking_pass`
   - `test_hook_runner_blocking_fail_aborts_step`
   - `test_agent_template_load_and_apply`
   - `test_scoped_permission_deny_path_outside_scope`
   - `test_scoped_permission_deny_blocked_tool`
   - `test_multi_repo_agent_accesses_all_repos`
   - `test_checkpoint_conflict_detection`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] Plan mode: read-only analysis + step-by-step plan generation.
- [ ] Auto-compact: automatic context compression at 80% token budget.
- [ ] Hooks: pre/post event scripts with blocking/async modes.
- [ ] Agent templates: 5 built-in + user-defined templates.
- [ ] Multi-repo: sub-agents operate across multiple local repos.
- [ ] Scoped permissions: path/tool/write restrictions per sub-agent.
- [ ] Checkpoint enhancement: conflict detection, selective save.
- [ ] All tests pass. Source files under 300 lines.
