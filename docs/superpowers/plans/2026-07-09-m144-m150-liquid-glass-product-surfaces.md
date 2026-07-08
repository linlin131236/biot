# M144-M150 Liquid Glass Product Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the liquid glass shell from a polished home screen into a coherent desktop product surface covering settings, permissions, patch review, audit, diagnostics, validation, memory, team, and final UI dogfood.

**Architecture:** Keep the existing `LiquidGlassWorkbench` shell and add focused settings/product surface modules instead of rewriting the app. Each milestone adds visible Chinese UI, tests, docs, and no new automatic execution capability.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, lucide-react, existing liquid glass CSS primitives, markdown review gates.

---

### Task 0: Baseline Repair

**Files:**
- Modify: `docs/project-state.md`

- [x] Correct the pushed M143 baseline from `57d6c04` to `61ecee1`.
- [x] Run `node scripts/check-docs.mjs`.
- [x] Run `git diff --check`.
- [x] Commit as `docs: correct M143 pushed baseline`.

### Task 1: M144 Settings Productization

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/144-settings-productization.md`
- Create: `docs/decisions/144-settings-productization.md`
- Create: `docs/phase-144-review-gate.md`

- [ ] Add failing tests that click 常规, 代码预览, 模型设置 and expect section-specific Chinese content.
- [ ] Implement section rendering with stable cards, safety copy, and no secret display.
- [ ] Run targeted desktop tests.
- [ ] Commit M144.

### Task 2: M145 Permission Center Surface

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/145-permission-center-surface.md`
- Create: `docs/decisions/145-permission-center-surface.md`
- Create: `docs/phase-145-review-gate.md`

- [ ] Add failing tests for 权限中心 cards: 待批准、写入门禁、审计记录.
- [ ] Implement permission center as a read-only high-trust surface.
- [ ] Run targeted desktop tests.
- [ ] Commit M145.

### Task 3: M146 Patch Review Surface

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/146-patch-review-surface.md`
- Create: `docs/decisions/146-patch-review-surface.md`
- Create: `docs/phase-146-review-gate.md`

- [ ] Add failing tests for 补丁预览, 风险摘要, 人工批准.
- [ ] Implement patch review surface without apply buttons that bypass approval.
- [ ] Run targeted desktop tests.
- [ ] Commit M146.

### Task 4: M147 Audit And Diagnostics Surface

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/147-audit-diagnostics-surface.md`
- Create: `docs/decisions/147-audit-diagnostics-surface.md`
- Create: `docs/phase-147-review-gate.md`

- [ ] Add failing tests for 审计时间线, 诊断中心, 恢复建议.
- [ ] Implement audit and diagnostics surface with clear status hierarchy.
- [ ] Run targeted desktop tests.
- [ ] Commit M147.

### Task 5: M148 Validation And Release Surface

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/148-validation-release-surface.md`
- Create: `docs/decisions/148-validation-release-surface.md`
- Create: `docs/phase-148-review-gate.md`

- [ ] Add failing tests for 验证门禁, 发布准备, 只读检查.
- [ ] Implement validation and release readiness surface that does not run push/release/tag.
- [ ] Run targeted desktop tests.
- [ ] Commit M148.

### Task 6: M149 Memory Team Queue Surface

**Files:**
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/liquidGlassSettings.css`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- Create: `docs/exec-plans/active/149-memory-team-queue-surface.md`
- Create: `docs/decisions/149-memory-team-queue-surface.md`
- Create: `docs/phase-149-review-gate.md`

- [ ] Add failing tests for 记忆索引, 多 Agent 团队, 多任务队列.
- [ ] Implement memory/team/queue surface with read-only operational cards.
- [ ] Run targeted desktop tests.
- [ ] Commit M149.

### Task 7: M150 UI Dogfood Review

**Files:**
- Modify: `docs/project-state.md`
- Create: `docs/exec-plans/active/150-liquid-glass-ui-dogfood.md`
- Create: `docs/decisions/150-liquid-glass-ui-dogfood.md`
- Create: `docs/phase-150-review-gate.md`

- [ ] Run targeted desktop tests.
- [ ] Run `pnpm --filter @bolt/desktop build`.
- [ ] Run `pnpm run quality`.
- [ ] Run `node scripts/check-chinese-ui.mjs`.
- [ ] Run `git diff --check`.
- [ ] Scan for private wording in product source.
- [ ] Update `docs/project-state.md`.
- [ ] Commit M150.
