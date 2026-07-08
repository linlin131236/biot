# M142 Liquid Glass Component System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Liquid Glass primitive component layer for the desktop UI.

**Architecture:** Keep the existing M141 shell, then extract repeated button, pill, panel, and toolbar patterns into small React primitives. Styling stays in the existing Liquid Glass CSS system and uses shared tokens instead of page-local one-off rules.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, CSS tokens.

---

### Task 1: Primitive Contract

**Files:**
- Create: `apps/desktop/src/LiquidGlassPrimitives.test.tsx`
- Create: `apps/desktop/src/LiquidGlassPrimitives.tsx`
- Modify: `apps/desktop/src/liquidGlassShell.css`

- [ ] **Step 1: Write the failing test**

```tsx
render(<GlassButton variant="primary">开始任务</GlassButton>);
expect(screen.getByRole('button', { name: '开始任务' })).toHaveClass('biotGlassButton', 'is-primary');
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --filter @bolt/desktop test -- LiquidGlassPrimitives.test.tsx`

Expected: fail because `LiquidGlassPrimitives` does not exist.

- [ ] **Step 3: Implement primitives**

Create `GlassButton`, `GlassPanel`, `GlassPill`, and `GlassToolbar` with typed props and stable class contracts.

- [ ] **Step 4: Run the primitive test again**

Expected: pass.

### Task 2: Home Integration

**Files:**
- Modify: `apps/desktop/src/LiquidGlassHome.tsx`
- Test: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`

- [ ] Replace home chips and command buttons with primitives.
- [ ] Keep all existing button callbacks and disabled states.
- [ ] Confirm task input, start goal, create goal, and step actions still pass.

### Task 3: Settings Integration

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Test: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`

- [ ] Replace settings cards and tabs with primitives.
- [ ] Keep settings categories and all Chinese labels unchanged.
- [ ] Confirm settings view still renders the approved categories.

### Task 4: Verification And Docs

**Files:**
- Create: `docs/exec-plans/active/142-liquid-glass-component-system.md`
- Create: `docs/decisions/142-liquid-glass-component-system.md`
- Create: `docs/phase-142-review-gate.md`
- Modify: `docs/project-state.md`

- [ ] Run targeted desktop tests.
- [ ] Run desktop build.
- [ ] Run `pnpm run quality`.
- [ ] Run `uv run pytest -q` if backend-visible text changes.
- [ ] Confirm no private称呼 appears in product source.
- [ ] Commit M142 only after verification passes.
