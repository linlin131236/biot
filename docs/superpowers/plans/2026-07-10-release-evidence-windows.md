# Release Evidence and Windows Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个 Bolt Windows 候选构建生成脱敏、机器可验证的 Release Evidence，并在隔离 Windows 用户中完成安装、重启、真实模型、权限、Diff、回滚和卸载验收。

**Architecture:** Python evidence writer 生成严格 schema 的 manifest/check/events；Node preflight 汇总构建哈希；Desktop 提供只读验收状态。自动检查和人工检查使用相同 check ID，只有全部 `passed` 才允许标记安全受控 Beta。

**Tech Stack:** Python JSON/NDJSON/hashlib、Pydantic、Node.js、Electron Builder/NSIS、pytest/Vitest、GitHub Actions Windows runner。

---

### Task 1: Define the evidence schema and redaction boundary

**Files:**
- Create: `services/agent-core/src/bolt_core/release_evidence_models.py`
- Create: `services/agent-core/src/bolt_core/release_evidence_redaction.py`
- Create: `services/agent-core/tests/test_release_evidence_models.py`
- Create: `services/agent-core/tests/test_release_evidence_redaction.py`

- [ ] **Step 1: Write failing schema and secret-leak tests**

```python
def test_not_run_and_blocked_do_not_count_as_passed():
    report = EvidenceChecks(checks=[
        EvidenceCheck(id="a", status="passed"),
        EvidenceCheck(id="b", status="not_run"),
    ])
    assert report.release_status == "failed"


def test_redactor_removes_authorization_keys_paths_and_prompt_text():
    event = redact_event({
        "authorization": "Bearer secret",
        "api_key": "sk-secret",
        "prompt": "private source",
        "path": r"C:\\Users\\Alice\\project",
    })
    encoded = json.dumps(event)
    assert "secret" not in encoded
    assert "private source" not in encoded
    assert "Alice" not in encoded
```

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_models.py tests/test_release_evidence_redaction.py -v
```

- [ ] **Step 3: Implement strict evidence models**

Pydantic models use `extra="forbid"`; status is `passed|failed|blocked|not_run`. Evidence references are relative paths or `events.ndjson#event-id`. Redaction uses allowlisted output fields rather than only blacklist replacement; provider ID is SHA-256 with per-report salt, paths are reduced to role names (`workspace`, `user_data`, `install_dir`).

- [ ] **Step 4: Run tests**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_models.py tests/test_release_evidence_redaction.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add services/agent-core/src/bolt_core/release_evidence_models.py services/agent-core/src/bolt_core/release_evidence_redaction.py services/agent-core/tests/test_release_evidence_models.py services/agent-core/tests/test_release_evidence_redaction.py
git commit -m "feat: define redacted release evidence schema"
```

### Task 2: Implement atomic evidence writing

**Files:**
- Create: `services/agent-core/src/bolt_core/release_evidence_store.py`
- Create: `services/agent-core/tests/test_release_evidence_store.py`

- [ ] **Step 1: Write red atomicity and path tests**

```python
def test_evidence_store_writes_required_files_atomically(tmp_path):
    store = ReleaseEvidenceStore(tmp_path)
    report_dir = store.create("0.1.0", "abc123", now=fixed_time)
    store.write_manifest(report_dir, manifest)
    store.write_checks(report_dir, checks)
    store.append_event(report_dir, event)
    assert {p.name for p in report_dir.iterdir()} >= {
        "manifest.json", "checks.json", "events.ndjson", "logs", "screenshots"
    }


def test_evidence_reference_cannot_escape_report_directory(tmp_path): ...
```

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_store.py -v
```

- [ ] **Step 3: Implement store**

Use `<version>-<commit>-<UTC timestamp>` names, temp sibling files plus `os.replace`, UTF-8 and final newlines. Refuse symlinks and `..` evidence paths. `append_event` writes one already-redacted event per line and flushes.

- [ ] **Step 4: Run tests**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_store.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/agent-core/src/bolt_core/release_evidence_store.py services/agent-core/tests/test_release_evidence_store.py
git commit -m "feat: write release evidence atomically"
```

### Task 3: Add build artifact and contract hashing

**Files:**
- Create: `scripts/create-release-evidence.mjs`
- Create: `scripts/create-release-evidence.test.mjs`
- Modify: `scripts/release-preflight.mjs`
- Modify: `apps/desktop/package.json`
- Modify: `package.json`

- [ ] **Step 1: Write a red Node test**

Use temporary files and assert SHA-256 records for NSIS/portable, `openapi.json`, generated client directory manifest and Git commit. Assert missing required artifacts produce `blocked`, not `passed`.

- [ ] **Step 2: Verify red**

```bash
node --test scripts/create-release-evidence.test.mjs
```

- [ ] **Step 3: Implement deterministic hashing**

Hash files by bytes; hash directories by sorted relative path + per-file hash. Write `artifacts.json` and `environment.json`. Add root script:

```json
"evidence:create": "node scripts/create-release-evidence.mjs"
```

Package scripts invoke evidence creation after successful builder output, never before.

- [ ] **Step 4: Run tests and package runtime lint**

```bash
node --test scripts/create-release-evidence.test.mjs
pnpm lint:package-runtime
```

- [ ] **Step 5: Commit**

```bash
git add scripts/create-release-evidence.mjs scripts/create-release-evidence.test.mjs scripts/release-preflight.mjs apps/desktop/package.json package.json
git commit -m "feat: hash release artifacts into evidence"
```

### Task 4: Expose read-only evidence status in Desktop

**Files:**
- Create: `services/agent-core/src/bolt_core/release_evidence_api.py`
- Create: `services/agent-core/tests/test_release_evidence_api.py`
- Modify: `services/agent-core/src/bolt_core/app.py`
- Create: `apps/desktop/src/settings/ReleaseEvidencePage.tsx`
- Create: `apps/desktop/src/settings/ReleaseEvidencePage.test.tsx`
- Modify: `apps/desktop/src/settings/settingsCatalog.ts`

- [ ] **Step 1: Write red backend and Desktop tests**

Backend must return latest report summary and checks without absolute paths or event payloads. Desktop must show each status and refuse to label a report ready when any item is not passed.

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_api.py -v
pnpm --filter @bolt/desktop test -- ReleaseEvidencePage.test.tsx
```

- [ ] **Step 3: Implement read-only API and page**

Provide only GET routes. The Desktop page can open the local evidence directory through an explicit narrow Electron shell action if implemented; it must not edit checks or mark them passed.

- [ ] **Step 4: Run tests**

```bash
cd services/agent-core && uv run pytest tests/test_release_evidence_api.py -v
pnpm --filter @bolt/desktop test -- ReleaseEvidencePage.test.tsx SettingsShell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add services/agent-core/src/bolt_core/release_evidence_api.py services/agent-core/src/bolt_core/app.py services/agent-core/tests/test_release_evidence_api.py apps/desktop/src/settings/ReleaseEvidencePage.tsx apps/desktop/src/settings/ReleaseEvidencePage.test.tsx apps/desktop/src/settings/settingsCatalog.ts
git commit -m "feat: show release evidence in bolt desktop"
```

### Task 5: Automate non-GUI Windows checks

**Files:**
- Create: `scripts/windows-acceptance.ps1`
- Create: `scripts/windows-uninstall-audit.ps1`
- Create: `scripts/windows-acceptance.tests.ps1`
- Modify: `.github/workflows/release.yml`
- Modify: `docs/release/release-checklist.md`

- [ ] **Step 1: Write Pester tests for process and residue checks**

The script functions must detect:

- Bolt and Python child processes still alive after exit.
- Missing packaged Core files.
- Unexpected startup tasks/services.
- Installer hash mismatch.
- Program directory residue after uninstall.
- User-data handling inconsistent with the selected keep/delete option.

- [ ] **Step 2: Verify red**

```powershell
Invoke-Pester scripts/windows-acceptance.tests.ps1
```

Expected: functions missing.

- [ ] **Step 3: Implement scripts with explicit check IDs**

Use IDs:

```text
install.nsis
startup.core
exit.no-child-process
restart.credential
model.real-call
permission.reject-no-change
permission.approve-diff
rollback.restore
credential.delete
uninstall.program-files
uninstall.processes
uninstall.user-data-choice
```

Automation writes results through a small CLI entry in the evidence store. It must never accept a key argument. Real-call and GUI checks remain `not_run` until performed interactively in Bolt.

- [ ] **Step 4: Run Pester and CI-safe checks**

```powershell
Invoke-Pester scripts/windows-acceptance.tests.ps1
```

Expected: pass.

- [ ] **Step 5: Update release workflow and commit**

CI creates build/artifact evidence and uploads it with packages, but does not claim GUI/manual checks passed. Then:

```bash
git add scripts/windows-acceptance.ps1 scripts/windows-uninstall-audit.ps1 scripts/windows-acceptance.tests.ps1 .github/workflows/release.yml docs/release/release-checklist.md
git commit -m "feat: automate windows beta acceptance evidence"
```

### Task 6: Prepare the isolated Windows user acceptance run

**Files:**
- Create: `docs/release/safe-beta-acceptance-runbook.md`
- Create: `docs/release/evidence-check-catalog.json`
- Modify: `apps/desktop/electron-builder.json`

- [ ] **Step 1: Define exact preconditions**

The runbook requires a new local Windows user, no Bolt processes, empty Bolt install/user-data directories, no reused workspace `.bolt`, installer SHA match, and a disposable test workspace. It explicitly says the user enters the real key only in Bolt Desktop.

- [ ] **Step 2: Configure explicit uninstall behavior**

Keep workspace files always. For app user data, provide an explicit keep/delete choice; if NSIS configuration cannot safely provide this in the current builder version, default to keeping data and document/manual-test that behavior rather than silently deleting.

- [ ] **Step 3: Define exact GUI evidence for each check**

For each check list action, expected state, allowed screenshot, prohibited sensitive content and machine event reference. The real model screenshot shows provider/model/status/latency only; prompts and API keys must be absent.

- [ ] **Step 4: Validate catalog against schema**

Add a test or script invocation that loads every check catalog entry into `EvidenceCheck` and asserts all stage-A exit criteria have one check ID.

- [ ] **Step 5: Commit**

```bash
git add docs/release/safe-beta-acceptance-runbook.md docs/release/evidence-check-catalog.json apps/desktop/electron-builder.json
git commit -m "docs: define isolated windows beta acceptance run"
```

### Task 7: Execute automated release verification

**Files:**
- Generated: `release-evidence/<version>-<commit>-<timestamp>/**`
- Do not commit evidence containing machine-specific test output unless repository policy explicitly requires it; upload as release artifact instead.

- [ ] **Step 1: Confirm branch and working-tree ownership**

```bash
git branch --show-current
git status --short
```

Expected: `feat/safe-controlled-beta`; review every existing modified file before staging.

- [ ] **Step 2: Run quality**

```bash
pnpm quality
```

Expected: exit 0. If not, evidence records the exact failed gate and remains failed.

- [ ] **Step 3: Build Desktop and backend tests in isolated mode**

```bash
pnpm --filter @bolt/desktop build
cd services/agent-core && .venv/Scripts/python -I -m pytest
```

Expected: exit 0.

- [ ] **Step 4: Build dir and NSIS artifacts**

```bash
pnpm --filter @bolt/desktop package:win:dir
pnpm --filter @bolt/desktop package:win:nsis
```

Expected: package runtime check passes and installer exists.

- [ ] **Step 5: Create evidence and verify redaction**

```bash
pnpm evidence:create
```

Then scan the evidence directory for forbidden markers using generated fake canaries introduced only for the scan; no real key is used. Expected: zero matches.

### Task 8: Execute the manual isolated Windows run

**Files:**
- Update only the external/generated evidence directory.

- [ ] **Step 1: Install under the clean Windows user**

Verify `install.nsis` and `startup.core`; capture installer hash and a non-sensitive first-start screenshot.

- [ ] **Step 2: Save and verify a real provider locally**

The user enters the API Key in Bolt Desktop. Run one minimum-cost request. Record only provider hash, model, status, latency and token counts.

- [ ] **Step 3: Verify restart credential continuity**

Exit Bolt, prove no child process remains, restart, and run the same minimal request without re-entering the key.

- [ ] **Step 4: Verify permission, Diff and rollback**

In a disposable workspace: request one controlled write, reject and hash-prove no change; repeat, approve after reviewing Diff, hash-prove expected change; rollback and hash-prove original restoration.

- [ ] **Step 5: Delete provider credentials**

Delete the provider or key, verify status becomes unconfigured and a new model call fails with `credential_missing` without leaking the secret.

- [ ] **Step 6: Uninstall and audit residue**

Verify no process, service or startup entry remains; verify program files behavior and the explicit user-data choice; never delete the disposable workspace as an implicit uninstall side effect.

- [ ] **Step 7: Close the report**

All Stage A IDs must be `passed`. Any `failed`, `blocked` or `not_run` makes final status failed. Sign with tester name/alias, UTC completion time and installer SHA.

### Task 9: Final adversarial review and decision

**Files:**
- Create: `docs/decisions/184-safe-controlled-beta-release-evidence.md`
- Modify: `docs/project-state.md`

- [ ] **Step 1: Review attack and recovery cases**

Explicitly verify report results for DNS rebinding, redirects, Core-port targeting, provider response limits, concurrent save/delete, credential migration interruption, Core restart, permission race, rollback failure and uninstall residue.

- [ ] **Step 2: Run final gates once more against the exact commit**

```bash
pnpm quality
pnpm --filter @bolt/desktop build
```

Record exact commit and artifact hashes; do not rebuild after signing evidence without producing a new report.

- [ ] **Step 3: Update project truthfully**

Only mark “安全受控 Beta” if every required check passed. Otherwise list blockers and keep the prior status.

- [ ] **Step 4: Commit only docs, not sensitive evidence**

```bash
git add docs/decisions/184-safe-controlled-beta-release-evidence.md docs/project-state.md
git commit -m "docs: record safe controlled beta evidence result"
```
