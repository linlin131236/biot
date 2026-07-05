# Exec Plan 028 - Goal Mode: Persistent Long-Running Autonomous Tasks

## Goal

Add a `/goal` command to Bolt that enables persistent, long-running autonomous task loops. Unlike a regular prompt (one question → one answer), a Goal spawns a continuous loop of **plan → act → test → review → iterate** until the objective is met or a budget/stop condition triggers.

Inspired by Codex `/goal` (0.128.0 release, April 2026).

## Why Now

Bolt's current `agent_loop.py` has `max_steps=3` and no concept of a persistent objective. It runs 3 tool calls and stops. For real work (migrate a codebase, build a feature, fix 50 failing tests), the agent needs to:

1. Remember what it's trying to achieve across many steps
2. Self-correct when tests fail (not stop and ask)
3. Track evidence of progress (test results, files changed)
4. Know when to stop (completion criteria met, or budget exhausted)

This is the single highest-impact feature for making Bolt feel like a real autonomous agent.

## Architecture

```
/goal Migrate all Pydantic v1 models to v2 and ensure tests pass
    ↓
┌─────────────────────────────────────────────────┐
│ GoalRunner                                       │
│                                                  │
│  goal: "Migrate Pydantic v1→v2, tests pass"     │
│  completion_criteria: "All tests pass, no v1 imports" │
│  budget: { max_steps: 100, max_cost: $5.00 }    │
│  state: running | paused | completed | failed    │
│                                                  │
│  Loop:                                           │
│    1. Assess current state (read files, run tests)│
│    2. Plan next action toward goal               │
│    3. Execute action (edit, shell, etc.)          │
│    4. Verify progress (run tests, check criteria) │
│    5. Self-correct if needed                      │
│    6. Check completion / budget                   │
│    7. If not done → goto 1                        │
│                                                  │
│  Audit:                                          │
│    - Evidence log (test results, file diffs)      │
│    - Step counter + cost tracker                  │
│    - Completion audit before declaring "done"     │
└─────────────────────────────────────────────────┘
```

## Scope

### 1. Goal Definition

New file: `services/agent-core/src/bolt_core/goal.py`

```python
@dataclass
class Goal:
    objective: str              # Natural language description
    completion_criteria: str    # How to verify the goal is met
    constraints: list[str]      # What must NOT happen (e.g., "no breaking API changes")
    max_steps: int = 100        # Safety: max iterations
    max_cost: float = 5.0       # Safety: max $ spend
    max_wall_time: int = 3600   # Safety: max seconds (1 hour default)
    workspace: str = ""         # Working directory
    allowed_tools: list[str]    # Tools the goal runner can use
    auto_approve: bool = False  # Skip permission gate for each step?

class GoalBuilder:
    """Helps users write good goals. Inspired by Codex's requirement that
    goals must be 'audit-ready' before starting."""
    
    def build(self, raw_objective: str) -> Goal:
        # If objective is vague (e.g., "improve the dashboard"),
        # use LLM to help user clarify:
        # 1. What files are affected?
        # 2. What does success look like?
        # 3. What tests verify completion?
        # 4. What should NOT break?
        # Returns a structured Goal with completion_criteria
        pass
    
    def is_audit_ready(self, goal: Goal) -> tuple[bool, str]:
        # Check if goal is specific enough for autonomous execution
        # Vague goals are dangerous in full-auto mode
        pass
```

### 2. Goal Runner (The Core Loop)

New file: `services/agent-core/src/bolt_core/goal_runner.py`

```python
class GoalRunner:
    def __init__(self, goal: Goal, gateway, tool_executor, permission_gate, cost_tracker, memory):
        self.goal = goal
        self.gateway = gateway
        self.tools = tool_executor
        self.gate = permission_gate
        self.costs = cost_tracker
        self.memory = memory
        self.state = "idle"          # idle | running | paused | completed | failed
        self.step_count = 0
        self.evidence_log: list[Evidence] = []
        self.plan: list[str] = []    # Current step plan
    
    def run(self) -> GoalResult:
        self.state = "running"
        
        while self.state == "running":
            # Safety checks
            if self.step_count >= self.goal.max_steps:
                self.state = "failed"
                break
            if self.costs.total() >= self.goal.max_cost:
                self._budget_wrap_up()
                break
            if time.time() - self.start_time >= self.goal.max_wall_time:
                self._timeout_wrap_up()
                break
            
            # Step 1: Assess current state
            assessment = self._assess()
            
            # Step 2: Check completion
            if self._check_completion(assessment):
                self.state = "completed"
                break
            
            # Step 3: Plan next action
            action = self._plan_next(assessment)
            
            # Step 4: Execute (with permission gate if not auto_approve)
            result = self._execute(action)
            
            # Step 5: Record evidence
            self._record_evidence(action, result)
            
            # Step 6: Self-correct if needed
            if result.status == "failed":
                correction = self._plan_correction(result)
                correction_result = self._execute(correction)
                self._record_evidence(correction, correction_result)
            
            self.step_count += 1
        
        return self._build_result()
    
    def pause(self) -> None:
        self.state = "paused"
    
    def resume(self) -> None:
        if self.state == "paused":
            self.state = "running"
            self.run()
    
    def status(self) -> GoalStatus:
        return GoalStatus(
            state=self.state,
            step=self.step_count,
            max_steps=self.goal.max_steps,
            cost=self.costs.total(),
            max_cost=self.goal.max_cost,
            elapsed=int(time.time() - self.start_time),
            evidence_count=len(self.evidence_log),
        )
    
    def _assess(self) -> Assessment:
        # Read current state: run tests, check files, search code
        # Uses LLM to evaluate: "Where are we relative to the goal?"
        pass
    
    def _check_completion(self, assessment: Assessment) -> bool:
        # LLM evaluates: "Is the completion_criteria met?"
        # Must be EVIDENCE-BASED, not model guessing
        # E.g., "Do all tests pass?" → actually run pytest
        # E.g., "No v1 imports?" → actually grep for pydantic.v1
        pass
    
    def _plan_next(self, assessment: Assessment) -> Action:
        # LLM plans the next action given current state + goal
        # Returns a structured Action (tool_call + reasoning)
        pass
    
    def _execute(self, action: Action) -> StepResult:
        # Execute tool call through tool_executor
        # If not auto_approve, go through permission_gate
        pass
    
    def _plan_correction(self, failed_result: StepResult) -> Action:
        # LLM analyzes failure and plans correction
        # "The test failed because X, so I need to fix Y"
        pass
    
    def _record_evidence(self, action: Action, result: StepResult) -> None:
        # Log: what was done, what happened, test results, diffs
        # This is the audit trail
        pass
    
    def _budget_wrap_up(self) -> None:
        # Budget running out → LLM summarizes progress + remaining work
        # Sets state to "failed" with helpful message
        pass
```

### 3. Goal System Prompt

The LLM needs a specialized system prompt when running in goal mode:

```
You are Bolt Goal Runner, an autonomous agent working toward a specific objective.

## Your Goal
{goal.objective}

## Completion Criteria
{goal.completion_criteria}

## Constraints
{goal.constraints}

## Current State
Step: {step_count}/{max_steps}
Cost: ${current_cost}/${max_cost}
{recent_evidence_summary}

## Rules
1. Every action must move toward the completion criteria.
2. After each action, verify progress with concrete evidence (test results, file diffs).
3. If an action fails, analyze the error and try a different approach.
4. Do NOT repeat the same failed approach more than twice.
5. Do NOT declare the goal complete without running verification (tests, checks).
6. If you're stuck after 3 attempts at the same sub-problem, report the blocker.
7. Keep track of what you've already done — don't re-do completed work.
8. When budget is low, wrap up current work cleanly rather than starting new work.

## Available Tools
{tool_descriptions}
```

### 4. Evidence Log

Every step produces structured evidence that can be audited later:

```python
@dataclass
class Evidence:
    step: int
    action: str           # "Edited src/models.py: replaced BaseModel with pydantic_v2"
    result: str           # "Success" or error message
    test_output: str | None  # pytest output if tests were run
    files_changed: list[str] # list of modified files
    timestamp: str
    
class EvidenceLog:
    def add(self, evidence: Evidence) -> None
    def recent(self, n: int = 5) -> list[Evidence]
    def summary(self) -> str     # LLM-readable summary for context
    def full_log(self) -> str    # Complete audit trail
```

### 5. Goal Lifecycle Management

TUI + API controls:

| Command | What it does |
|---|---|
| `/goal <objective>` | Create and start a new goal |
| `/goal status` | Show current goal progress (steps, cost, evidence count) |
| `/goal pause` | Pause the running goal |
| `/goal resume` | Resume a paused goal |
| `/goal clear` | Abandon current goal |
| `/goal evidence` | Show evidence log |
| `/goal budget` | Show budget usage |

API endpoints:
- `POST /goals` — create goal
- `GET /goals/current` — current goal status
- `POST /goals/current/pause` — pause
- `POST /goals/current/resume` — resume
- `DELETE /goals/current` — abandon
- `GET /goals/current/evidence` — evidence log

### 6. Goal Persistence (Survives Session Interruption)

Goals are persisted to disk so they survive crashes or session closures:

```python
class GoalPersistence:
    def save(self, runner: GoalRunner) -> None:
        # Save to ~/.bolt/goals/{goal_id}/
        # Includes: goal definition, step count, evidence log, memory snapshot
        pass
    
    def load(self, goal_id: str) -> GoalRunner:
        # Restore from disk
        # Detect file conflicts (files changed since last save)
        pass
    
    def list(self) -> list[GoalSummary]:
        pass
```

On startup, Bolt checks for unfinished goals and offers to resume them.

### 7. Integration with Existing Systems

- **CostTracker** (Plan 026): GoalRunner checks budget each step
- **AutoCompact** (Plan 027): GoalRunner uses auto-compact for long sessions
- **PermissionGate**: Each action goes through gate (unless `auto_approve=True`)
- **MemoryStore**: GoalRunner stores intermediate findings in memory
- **CheckpointManager** (Plan 026): Auto-checkpoint every 10 steps
- **MoAGateway** (Plan 026): `/goal` can optionally use MoA for complex planning steps
- **Hooks** (Plan 027): `post_step` hook fires after each goal step

### 8. Desktop UI Updates

File: `apps/desktop/src/` (React components)

New components:
- `GoalPanel.tsx` — shows current goal status, progress bar, step count, cost
- `EvidenceTimeline.tsx` — scrollable audit trail of actions + results
- `GoalControls.tsx` — pause/resume/clear buttons

The desktop UI should show:
- Goal objective (pinned at top)
- Progress: step X/100, $X.XX/$5.00
- Current action being taken
- Last 5 evidence entries
- Pause/Resume/Clear buttons

## Safety Boundary

- **max_steps=100** default: prevents infinite loops even if completion check is buggy
- **max_cost=$5.00** default: prevents runaway API spending
- **max_wall_time=3600s** default: prevents running forever
- **Completion audit**: LLM must provide EVIDENCE (test results, file checks) before declaring done. "I think it's done" is NOT sufficient.
- **Self-correction limit**: If the same sub-problem fails 3 times, stop and report blocker instead of looping forever.
- **Permission gate still applies**: Unless `auto_approve=True`, each action needs user approval. For long-running tasks, recommend `auto_approve` on a git branch.
- **Git branch recommended**: UI should warn if running `/goal` on main/master branch.
- **Evidence is immutable**: Once logged, evidence entries cannot be modified or deleted.
- **Budget wrap-up**: When approaching budget limit, LLM wraps up current work cleanly instead of starting new work.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_goal_builder_structures_vague_objective`
   - `test_goal_builder_rejects_unauditably_vague_goal`
   - `test_goal_runner_completes_simple_goal`
   - `test_goal_runner_self_corrects_on_failure`
   - `test_goal_runner_stops_at_max_steps`
   - `test_goal_runner_stops_at_max_cost`
   - `test_goal_runner_checks_completion_with_evidence`
   - `test_goal_runner_pauses_and_resumes`
   - `test_goal_persistence_save_and_load`
   - `test_goal_persistence_detects_file_conflicts`
   - `test_evidence_log_records_each_step`
   - `test_evidence_log_summary_for_context`
   - `test_goal_lifecycle_create_pause_resume_clear`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `/goal <objective>` creates and starts a persistent autonomous loop
- [ ] GoalRunner loops plan→act→test→review→iterate until completion or budget exhausts
- [ ] Completion is evidence-based (tests pass, grep confirms, etc.), not model guessing
- [ ] Self-correction: failed actions trigger re-planning (max 3 retries per sub-problem)
- [ ] Safety: max_steps, max_cost, max_wall_time enforced
- [ ] `/goal status/pause/resume/clear/evidence/budget` commands work
- [ ] Goals persist to disk, survive session interruption, can be resumed
- [ ] Evidence log provides immutable audit trail
- [ ] GoalBuilder helps users write audit-ready objectives (rejects vague goals)
- [ ] Desktop UI shows goal progress, evidence timeline, controls
- [ ] All tests pass. Source files under 300 lines.
