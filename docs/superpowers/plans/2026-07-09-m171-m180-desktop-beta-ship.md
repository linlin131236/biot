# M171-M180 Desktop Beta Ship Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the M170 agent capability baseline into a desktop Beta release candidate gate that verifies installability, first-run setup, task flow, error handling, settings, recovery, performance, packaging readiness, dogfood, and final ship decision without auto release.

**Architecture:** Add a read-only `DesktopBetaShipService` that aggregates existing desktop, release, package, docs, and safety signals into M171-M180 checks. Expose one API route and one desktop panel so the app can show a Chinese release-candidate status without triggering push/release/tag/delete.

**Tech Stack:** Python FastAPI service/tests, React/Vitest desktop panel, existing `pnpm quality`, existing release/package scripts, docs review gates.

---

### Task 1: M171-M180 Backend Gate

**Files:**
- Create: `services/agent-core/src/bolt_core/desktop_beta_ship.py`
- Create: `services/agent-core/src/bolt_core/desktop_beta_ship_api.py`
- Modify: `services/agent-core/src/bolt_core/app.py`
- Test: `services/agent-core/tests/test_desktop_beta_ship.py`

- [ ] **Step 1: Write failing tests**

Create tests that assert:
- all 10 milestones M171-M180 are represented,
- checks are read-only and do not execute release commands,
- missing package scripts, docs, or startup assets produce blockers,
- API returns `ready`, `checks`, `blockers`, `next_step`.

- [ ] **Step 2: Run tests to verify RED**

Run: `uv run pytest services/agent-core/tests/test_desktop_beta_ship.py -q`

Expected: FAIL because service and route do not exist.

- [ ] **Step 3: Implement minimal backend**

Implement read-only filesystem checks only:
- M171 package smoke scripts exist.
- M172 first-run/setup surfaces exist.
- M173 real task flow surfaces exist.
- M174 error-state surfaces exist.
- M175 settings persistence/API exists.
- M176 audit/recovery surfaces exist.
- M177 performance/build budget signals exist.
- M178 installer readiness scripts exist and publish is `never`.
- M179 dogfood smoke tests/docs exist.
- M180 final docs chain exists.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest services/agent-core/tests/test_desktop_beta_ship.py -q`

Expected: PASS.

### Task 2: Desktop Ship Panel

**Files:**
- Create: `apps/desktop/src/DesktopBetaShipPanel.tsx`
- Create: `apps/desktop/src/DesktopBetaShipPanel.test.tsx`
- Modify: `apps/desktop/src/harnessClientAutonomy.ts`
- Modify: `apps/desktop/src/panelsApi.ts`
- Modify: `apps/desktop/src/PanelsSection.tsx`

- [ ] **Step 1: Write failing tests**

Test that the panel:
- uses injected authenticated `fetcher`,
- shows Chinese ready/blocker states,
- does not expose push/release/tag/delete buttons,
- groups M171-M180 checks.

- [ ] **Step 2: Run RED**

Run: `pnpm --filter @bolt/desktop test -- DesktopBetaShipPanel --run`

Expected: FAIL because component/client do not exist.

- [ ] **Step 3: Implement minimal panel**

Add a compact Chinese read-only panel with status, blockers, warnings, and next step.

- [ ] **Step 4: Verify GREEN**

Run: `pnpm --filter @bolt/desktop test -- DesktopBetaShipPanel --run`

Expected: PASS.

### Task 3: Docs Chain

**Files:**
- Create: `docs/exec-plans/active/171-desktop-package-smoke.md`
- Create: `docs/decisions/171-desktop-package-smoke.md`
- Create: `docs/phase-171-review-gate.md`
- Repeat equivalent files for M172-M180.
- Modify: `docs/project-state.md`

- [ ] **Step 1: Add docs**

Each milestone doc must state goal, safety boundary, validation, and no auto release.

- [ ] **Step 2: Verify docs**

Run: `node scripts/check-docs.mjs`

Expected: PASS.

### Task 4: Full Verification And Commit

**Files:**
- All touched files.

- [ ] **Step 1: Targeted tests**

Run backend and desktop targeted tests.

- [ ] **Step 2: Full gates**

Run:
- `uv run pytest -q`
- `pnpm run quality`
- `pnpm --filter @bolt/desktop build`
- `git diff --check`
- `node scripts/check-chinese-ui.mjs`

- [ ] **Step 3: Adversarial review**

Check for:
- auto push/release/tag/delete,
- PermissionGate bypass,
- renderer exposure,
- `as any` / `unknown as`,
- private user nickname in app UI,
- fake passing checks.

- [ ] **Step 4: Commit**

Commit with: `feat(M171-M180): add desktop beta ship readiness gate`

Do not push unless explicitly authorized.
