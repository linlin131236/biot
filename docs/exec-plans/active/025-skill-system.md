# Exec Plan 025 - Skill System

## Goal

Add a reusable skill system so Bolt can learn from successful task patterns, load specialized knowledge on demand, and improve over time — like Hermes's skill layer.

## Why Now

After Plans 019-024, Bolt has all the machinery of a real agent. But every conversation starts from zero knowledge about how to do specific tasks. Skills encode reusable workflows so Bolt doesn't re-learn the same patterns.

## Architecture

```
Agent receives task
    ↓
SkillMatcher.scan(task description, available skills)
    ↓ match found?
YES → load skill → inject into system prompt → execute
NO  → proceed normally → on success, offer to save as skill

Skill = Markdown file with:
  - YAML frontmatter (trigger keywords, tool requirements)
  - Body (step-by-step instructions, pitfalls, examples)
```

## Scope

### 1. Skill data model

New file: `services/agent-core/src/bolt_core/skill.py`

```python
@dataclass
class Skill:
    name: str               # "git-workflow"
    description: str
    triggers: list[str]     # ["git", "commit", "branch", "PR"]
    required_tools: list[str]  # ["shell.execute", "file.patch"]
    content: str            # The markdown body
    version: str = "1.0"
    
class SkillStore:
    def __init__(self, skill_dir: str):
        # Scan {skill_dir}/*.md files
        # Parse YAML frontmatter + body
    
    def match(self, task: str) -> list[Skill]:
        # Keyword matching against triggers
        # Return top 3 most relevant skills
    
    def load(self, name: str) -> Skill:
        # Load specific skill by name
    
    def save(self, skill: Skill) -> None:
        # Create/update skill file
```

### 2. Skill directory structure

```
~/.bolt/skills/
├── git-workflow/
│   └── SKILL.md
├── debugging/
│   └── SKILL.md
├── code-review/
│   └── SKILL.md
└── ...
```

Each `SKILL.md`:
```markdown
---
name: git-workflow
triggers: [git, commit, branch, PR, pull request]
required_tools: [shell.execute, file.patch]
version: 1.0
---

# Git Workflow

## Steps
1. Check current branch: `git branch --show-current`
2. Stage changes: `git add -A`
3. Commit with message: `git commit -m "..."`
4. Push: `git push origin <branch>`

## Pitfalls
- Never push to main directly
- Always pull before push to avoid conflicts
```

### 3. Skill injection into system prompt

Update `Planner`:
- After skill matching, append matched skill content to system prompt.
- Format: "## Loaded Skill: {name}\n{content}"
- Max 2 skills per conversation (avoid prompt bloat).

### 4. Auto-skill creation

After a successful multi-step task (3+ tool calls, no failures):
- LLM generates a skill draft from the conversation trace.
- Offer to user: "Save this workflow as a skill?"
- If approved, save to skill directory.

New tool:
```json
{
  "name": "skill.save",
  "description": "Save a successful workflow as a reusable skill.",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "triggers": {"type": "array", "items": {"type": "string"}},
      "content": {"type": "string"}
    },
    "required": ["name", "triggers", "content"]
  }
}
```

PermissionGate: `confirm` level (creating files).

### 5. Built-in skills (seed)

Ship with 5 starter skills:
1. `git-workflow` — commit, branch, PR
2. `debugging` — systematic debugging steps
3. `code-review` — review checklist
4. `testing` — write tests first, run, fix
5. `project-setup` — initialize new project structure

### 6. API endpoints

- `GET /skills` — list available skills
- `GET /skills/{name}` — load skill content
- `POST /skills` — save new skill
- `GET /skills/match?task=...` — find matching skills

### 7. Desktop UI

- "Skills" sidebar showing loaded and available skills.
- Toggle to enable/disable auto-skill suggestions.
- One-click skill creation from conversation.

## Safety Boundary

- Skills are read-only instructions, not executable code.
- Skill content is injected into the LLM prompt; the LLM still goes through PermissionGate for all actions.
- Skills cannot override safety rules.
- Auto-skill creation requires user approval.
- Skill directory is user-controlled; Bolt only writes to it with permission.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_skill_store_load_and_match`
   - `test_skill_injection_into_system_prompt`
   - `test_auto_skill_creation_from_trace`
   - `test_max_2_skills_per_conversation`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `SkillStore` with load/match/save.
- [ ] Skill directory structure and SKILL.md format.
- [ ] Skill injection into Planner system prompt (max 2).
- [ ] Auto-skill creation tool.
- [ ] 5 built-in seed skills.
- [ ] API endpoints for skill management.
- [ ] All tests pass.
