# Exec Plan 022 - Multi-Agent Delegation

## Goal

Enable Bolt to spawn sub-agents for parallel or isolated work, making it a true multi-agent system like Hermes.

## Why Now

After Plans 019-021, Bolt is a competent single agent. But real work benefits from parallelism: research one thing while building another, review code independently from writing it, run tests in the background while editing.

## Architecture

```
Main Agent (Harness run)
    ↓ delegate_task
SubAgentManager
    ↓ spawn
SubAgent (own Harness run, own workspace, own context)
    ↓ execute independently
    ↓ report summary back
Main Agent receives summary
```

## Scope

### 1. SubAgent data model

New file: `services/agent-core/src/bolt_core/sub_agent.py`

```python
@dataclass(frozen=True)
class SubAgentTask:
    id: str
    goal: str
    context: str        # injected context
    workspace: str
    toolset: list[str]  # which tools this sub-agent can use
    status: str         # pending / running / completed / failed
    result: str | None  # summary when done

class SubAgentManager:
    def __init__(self, harness: Harness):
        self.harness = harness
        self.tasks: dict[str, SubAgentTask] = {}
    
    def spawn(self, goal, context, workspace, toolset, max_steps=10) -> SubAgentTask:
        # Create a new Harness run with restricted toolset
        # Run in background thread
    
    def poll(self, task_id) -> SubAgentTask:
        # Check status
    
    def list(self) -> list[SubAgentTask]:
        # All sub-agent tasks
    
    def result(self, task_id) -> str:
        # Get summary, block if still running
```

### 2. `delegate_task` tool schema

```json
{
  "name": "delegate.task",
  "description": "Spawn a sub-agent to work on a task independently. Returns immediately with task_id.",
  "parameters": {
    "type": "object",
    "properties": {
      "goal": {"type": "string", "description": "What the sub-agent should accomplish"},
      "context": {"type": "string", "description": "Background information the sub-agent needs"},
      "toolset": {"type": "array", "items": {"type": "string"}, "description": "Tools the sub-agent can use"}
    },
    "required": ["goal"]
  }
}
```

### 3. `delegate.poll` tool schema

```json
{
  "name": "delegate.poll",
  "description": "Check status of a spawned sub-agent task.",
  "parameters": {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"}
    },
    "required": ["task_id"]
  }
}
```

### 4. Permission Gate updates

- `delegate.task` → `confirm` level (spawning agents costs resources).
- `delegate.poll` → `allow` level (read-only).
- Sub-agents inherit workspace permission scope from parent.
- Sub-agents CANNOT themselves delegate (max depth 1).

### 5. API endpoints

- `POST /delegate/spawn` — spawn sub-agent
- `GET /delegate/tasks` — list all sub-agent tasks
- `GET /delegate/tasks/{task_id}` — poll status
- `GET /delegate/tasks/{task_id}/trace` — get sub-agent trace

### 6. Desktop UI

Add "Sub-Agents" panel showing running tasks, status, progress.

## Safety Boundary

- Sub-agents go through the same PermissionGate as the main agent.
- Max concurrent sub-agents: 3 (configurable).
- Max depth: 1 (sub-agents cannot spawn sub-sub-agents).
- Sub-agents run in background threads, same process, same permission scope.
- All sub-agent traces are visible to the main agent and the user.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_sub_agent_spawn_and_poll`
   - `test_sub_agent_cannot_delegate`
   - `test_sub_agent_max_concurrent_3`
   - `test_sub_agent_summary_returned`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `SubAgentManager` with spawn/poll/list/result.
- [ ] `delegate.task` and `delegate.poll` tools.
- [ ] PermissionGate and risk updated.
- [ ] API endpoints for sub-agent management.
- [ ] Max depth 1, max concurrent 3 enforced.
- [ ] All tests pass.
