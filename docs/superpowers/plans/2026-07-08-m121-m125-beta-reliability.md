# M121-M125 Beta Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the V8 beta reliability closure from M121 through M125 without introducing automatic release, migration, rollback, or dangerous execution.

**Architecture:** Add five small read-only backend assessment services plus API routers. M121-M124 each checks one product reliability surface, and M125 aggregates the previous gates, documentation chain, safety scans, and the M126 boundary.

**Tech Stack:** Python dataclasses, FastAPI routers, pytest/httpx tests, existing Bolt docs and quality gates.

---

### File Structure

- Create `services/agent-core/src/bolt_core/beta_reliability_common.py` for shared `BetaCheck` and `BetaReviewResult`.
- Create `crash_recovery.py` / `_api.py` and tests for M121 crash recovery readiness.
- Create `data_migration.py` / `_api.py` and tests for M122 migration readiness.
- Create `update_rollback.py` / `_api.py` and tests for M123 update/rollback readiness.
- Create `privacy_security_audit.py` / `_api.py` and tests for M124 privacy/security audit.
- Create `public_beta_readiness.py` / `_api.py` and tests for M125 public beta gate.
- Modify `services/agent-core/src/bolt_core/app.py` only to register the new read-only routers.
- Add M121-M125 exec plans, decisions, review gates, and update `docs/project-state.md`.

### Task 1: Shared Result Model

- [ ] Write failing tests that expect `BetaReviewResult.to_dict()` to expose `checks`, counts, `all_passed`, `p1_failures`, `warnings`, and `next_step`.
- [ ] Implement `beta_reliability_common.py` with no file writes, no subprocess, and no side effects.
- [ ] Run the targeted shared result tests.

### Task 2: M121 Crash Recovery

- [ ] Write failing tests for a complete recovery project and a missing checkpoint file project.
- [ ] Implement read-only checks for checkpoint, pause/resume, session recovery, audit integrity, thread handoff, and docs.
- [ ] Add API test for `GET /reliability/crash-recovery`.
- [ ] Add M121 docs and commit.

### Task 3: M122 Data Migration

- [ ] Write failing tests for migration manifest coverage, raw/staging/clean lineage references, rollback plan, and no auto migration.
- [ ] Implement read-only migration readiness checks.
- [ ] Add API test for `GET /reliability/data-migration`.
- [ ] Add M122 docs and commit.

### Task 4: M123 Update/Rollback

- [ ] Write failing tests for update checklist, rollback policy, release readiness, approval gate, and no auto release/tag/delete.
- [ ] Implement read-only update/rollback checks.
- [ ] Add API test for `GET /reliability/update-rollback`.
- [ ] Add M123 docs and commit.

### Task 5: M124 Privacy/Security Audit

- [ ] Write failing tests for secret redaction, permission contract, renderer boundary, type escape scan, supply chain docs, and M124 references.
- [ ] Implement read-only privacy/security audit checks.
- [ ] Add API test for `GET /reliability/privacy-security-audit`.
- [ ] Add M124 docs and commit.

### Task 6: M125 Public Beta Readiness

- [ ] Write failing tests for aggregation of M121-M124, docs chain M121-M125, project-state, no M126, and final beta verdict.
- [ ] Implement public beta readiness aggregator.
- [ ] Add API test for `GET /reliability/public-beta-readiness`.
- [ ] Add M125 docs, final handoff, project-state update, and commit.

### Task 7: Final Verification

- [ ] Run targeted M121-M125 pytest files.
- [ ] Run `uv run pytest -q --color=no`.
- [ ] Run `pnpm --filter @bolt/shared test`.
- [ ] Run `pnpm --filter @bolt/desktop test`.
- [ ] Run `pnpm --filter @bolt/desktop build`.
- [ ] Run `pnpm run quality`.
- [ ] Run `git diff --check`, `node scripts/check-docs.mjs`, and `node scripts/check-chinese-ui.mjs`.
- [ ] Confirm no `as any` / `unknown as`, no renderer exposure, no automatic push/release/tag/delete, and no M126.
