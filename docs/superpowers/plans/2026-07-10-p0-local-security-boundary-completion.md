# Bolt P0 Local Security Boundary Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the interrupted P0 security slice by wiring the persisted workspace credential gate into production model calls, rotating every Agent Core generation, restoring the approved atomic-write boundary, and producing fresh verification evidence.

**Architecture:** A server-owned `LockedWorkspace` value is captured by the desktop composition and attached to every `ModelRequest` inside `Harness`/`AgentLoop`; callers and Renderer cannot supply it. `DefaultModelGateway` obtains a short-lived `CredentialLease` from `WorkspaceCredentialGate` before any provider client is constructed, and the gate revalidates persisted migration/provider revisions immediately before client construction. `AgentCoreSupervisor` creates a fresh runtime generation for every child spawn, while non-secret JSON stores delegate all mutations to the approved atomic-write module.

**Tech Stack:** Python 3.11, pytest, Electron, TypeScript, Vitest, Windows Credential Manager, Node architecture gate.

**Working-tree constraint:** Continue in the existing dirty `feat/safe-controlled-beta` checkout because the interrupted implementation is uncommitted. Do not commit, stage, reset, clean, or modify unrelated UI/CSS/Figma files.

---

### Task 1: Production workspace-bound credential resolution

**Files:**
- Modify: `services/agent-core/src/bolt_core/workspace_credential_gate.py`
- Modify: `services/agent-core/src/bolt_core/model_gateway.py`
- Modify: `services/agent-core/src/bolt_core/agent_loop.py`
- Modify: `services/agent-core/src/bolt_core/harness.py`
- Modify: `services/agent-core/src/bolt_core/app.py`
- Modify: `services/agent-core/src/bolt_core/desktop_runner.py`
- Test: `services/agent-core/tests/test_workspace_credential_gate.py`
- Test: `services/agent-core/tests/test_model_gateway.py`
- Test: `services/agent-core/tests/test_harness_workspace_credential_gate.py`

- [ ] **Step 1: Write failing gate tests**

Add tests proving persisted migration `workspace_revision` is distinct from journal revision, provider state is rechecked before client construction, blocked workspace B performs zero credential reads/client construction while workspace A succeeds, and a restarted persistent adapter preserves the decision.

- [ ] **Step 2: Run the RED tests**

Run:

```powershell
uv run pytest tests/test_workspace_credential_gate.py tests/test_model_gateway.py tests/test_harness_workspace_credential_gate.py -q
```

Expected: failures for missing persistent state adapter, missing locked workspace on `ModelRequest`, and the current `credential resolver required` response.

- [ ] **Step 3: Implement the minimal production chain**

Implement these contracts without putting the secret in `ModelConfig`:

```python
@dataclass(frozen=True)
class ModelRequest:
    messages: list[ModelMessage]
    config: ModelConfig
    locked_workspace: LockedWorkspace | None = None

class WorkspaceCredentialGate:
    def resolve(self, workspace: LockedWorkspace, provider: str) -> CredentialLease: ...
    def validate(self, workspace: LockedWorkspace, provider: str, lease: CredentialLease) -> None: ...
```

`Harness` supplies the server-owned lock to `AgentLoop`; production `DefaultModelGateway` rejects a missing lock, resolves a lease, validates it immediately before provider client construction, and maps `CredentialGateError` to the exact stable error string with zero network calls. Explicit unit-test fake composition may remain credential-free; desktop production must inject the persistent gate.

- [ ] **Step 4: Run focused GREEN tests**

Run the command from Step 2 and the existing agent-loop/harness suites. Expected: all selected tests pass with no secret in traces or responses.

### Task 2: Fresh secrets for every Agent Core restart

**Files:**
- Modify: `apps/desktop/electron/agentCoreRuntime.ts`
- Modify: `apps/desktop/electron/agentCoreRuntime.test.ts`
- Test: `apps/desktop/electron/agentCoreIpc.test.ts`

- [ ] **Step 1: Write the restart RED test**

Add one same-supervisor test that spawns generation 1, records startup ID/bootstrap/Bearer/environment, simulates exit, starts generation 2, and asserts all three secrets and the verified generation ID differ. Assert the old verified generation is revoked before the second spawn and old requests are not sent.

- [ ] **Step 2: Verify RED**

Run:

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run electron/agentCoreRuntime.test.ts electron/agentCoreIpc.test.ts
```

Expected: the restart test fails because the supervisor currently stores one immutable runtime.

- [ ] **Step 3: Implement per-spawn generation creation**

Keep immutable command/path configuration separate from generation material. Make the supervisor call a generation/runtime factory only when spawning a new child, use that runtime for readiness and verification, and clear its references on revoke. Do not expose secrets to preload/Renderer and do not change UI.

- [ ] **Step 4: Run focused GREEN tests**

Run the command from Step 2 plus `desktopStartup.test.ts`, `agentCoreReadiness.test.ts`, and `electronBridge.integration.test.ts`.

### Task 3: Approved atomic JSON persistence boundary

**Files:**
- Modify: `services/agent-core/src/bolt_core/atomic_write.py`
- Modify: `services/agent-core/src/bolt_core/credential_lifecycle.py`
- Modify: `services/agent-core/src/bolt_core/legacy_credential_migration.py`
- Test: `services/agent-core/tests/test_atomic_write.py`
- Test: `services/agent-core/tests/test_credential_lifecycle.py`
- Test: `services/agent-core/tests/test_legacy_credential_migration.py`
- Test: `scripts/check-architecture.mjs`

- [ ] **Step 1: Write atomic-persistence RED tests**

Add tests proving JSON writes use a unique same-directory temporary file, flush and `fsync` before `os.replace`, clean a failed temporary file, retain compare-and-swap revisions, and persist valid JSON across a fresh store instance.

- [ ] **Step 2: Verify RED and current architecture failure**

Run focused pytest files and `node scripts/check-architecture.mjs`. Expected: atomic helper behavior is missing and the architecture gate reports direct writes in `credential_lifecycle.py` and `legacy_credential_migration.py`.

- [ ] **Step 3: Route both stores through the approved boundary**

Add an `atomic_write_json(path, value)` helper in `atomic_write.py`; it serializes deterministic non-secret JSON and delegates to an fsync-before-replace implementation. Replace direct `Path.open(..., 'w')` and `os.replace` logic in both stores with this helper. Keep reads and revision checks in their owning stores.

- [ ] **Step 4: Run focused GREEN and architecture gate**

Expected: persistence tests pass and `node scripts/check-architecture.mjs` exits 0 without adding file-specific exemptions for the two stores.

### Task 4: Joint security verification and review

**Files:**
- Modify only if a failing in-scope regression test proves a P0 defect.
- Evidence: terminal outputs and final handoff; do not include secrets.

- [ ] **Step 1: Run focused Desktop P0 tests**

Run all eight existing P0 Electron/Renderer test files plus restart tests. Record exact file/test counts.

- [ ] **Step 2: Run focused backend P0 tests**

Run credential store, Credential Manager, lifecycle/API, migration, workspace gate, model secret boundary, local auth, desktop runner, settings, gateway, agent-loop and harness binding tests. Record exact count and warnings.

- [ ] **Step 3: Run static gates and build**

Run:

```powershell
node scripts/check-architecture.mjs
pnpm.cmd --filter @bolt/desktop build
git diff --check
```

- [ ] **Step 4: Run broader regression suites**

Run the full backend suite and full Desktop test suite. Separate pre-existing UI redesign failures from P0 regressions; do not claim a full green suite if either fails.

- [ ] **Step 5: Adversarial review**

Review for external URL control, global fetch fallback, stale generation reuse, missing locked workspace, migration-state downgrade, revision TOCTOU, secret leakage, direct credential file storage, and failure cleanup. Report Critical/Important/Minor findings and fix Critical/Important in scope through fresh RED-GREEN cycles.

- [ ] **Step 6: Release decision**

Mark the technical P0 slice complete only if every completion gate is evidenced. Continue to report player beta/public release as blocked while the separate editable Core URL UI gate or release evidence remains incomplete.
