# Bolt Player-Release UI Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all Renderer Core URL authority, show only “本地 Agent Core · 由 Bolt 自动管理”, make clients path-only, and bring `@bolt/desktop` full test suite to green without weakening P0 security.

**Architecture:** Delete `DesktopSession.coreUrl` and physically purge it from localStorage. Convert `coreClient` / `harnessClient` / `harnessClientAutonomy` / `workflowClient` / `panelsApi` / all panels to path-only APIs that never accept Agent Core `baseUrl`. Transport accepts only relative paths beginning with `/`; absolute URLs fail closed with zero IPC/network. Settings shows a read-only managed Core status; workbench shows only online/offline health. A static architecture gate forbids residual `coreUrl` / Agent Core `baseUrl` / `http://core` defaults in production sources.

**Tech Stack:** Electron, React, TypeScript, Vitest, Node architecture gate.

**Working-tree constraint:** Continue on dirty `feat/safe-controlled-beta`. Do not weaken P0 transport/credential/generation code. Do not claim player beta readiness after this slice. Prefer frequent commits for this slice only after focused green; do not stage unrelated dirty files.

**Spec:** `docs/superpowers/specs/2026-07-11-player-release-ui-gate-design.md`

---

## File structure and ownership

| Unit | Responsibility |
|------|----------------|
| `desktopSession.ts` | Session persistence without Core URL; physical purge of legacy field |
| `agentCoreAuth.ts` | Renderer transport; relative-path only; no absolute URL compatibility |
| `coreClient.ts` | Health client, path-only |
| `harnessClient.ts` | Core harness APIs, path-only |
| `harnessClientAutonomy.ts` | Autonomy APIs, path-only |
| `workflowClient.ts` | Workflow wrappers, path-only |
| `panelsApi.ts` | Bound panel API facade without URL args |
| `PanelsSection.tsx` + panels | UI composition without Agent Core URL props |
| `App.tsx` / LiquidGlass* | Product shell, managed Core copy, error text |
| `scripts/check-architecture.mjs` | Static ban on residual Core URL authority |

**Important distinction:** model provider field `base_url` / UI label `Base URL` is **provider endpoint**, not Agent Core URL. Keep it, but never name or treat it as Core endpoint.

---

### Task 1: Session removes and physically purges `coreUrl`

**Files:**
- Modify: `apps/desktop/src/desktopSession.ts`
- Modify: `apps/desktop/src/desktopSession.test.ts`

- [ ] **Step 1: Write failing session tests**

Replace `apps/desktop/src/desktopSession.test.ts` with:

```ts
import { describe, expect, it, beforeEach } from 'vitest';
import { loadDesktopSession, saveDesktopSession, SESSION_KEY } from './desktopSession';

beforeEach(() => {
  localStorage.clear();
});

describe('desktop session storage', () => {
  it('returns defaults for a fresh install without coreUrl', () => {
    expect(loadDesktopSession()).toEqual({
      completed: false,
      workspacePath: '',
      lastRunId: null,
    });
    expect(loadDesktopSession()).not.toHaveProperty('coreUrl');
  });

  it('persists non-sensitive first-run state without coreUrl', () => {
    saveDesktopSession({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_1',
    });

    expect(loadDesktopSession()).toEqual({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_1',
    });
    const raw = localStorage.getItem(SESSION_KEY) ?? '';
    expect(raw).not.toContain('api_key');
    expect(raw).not.toContain('coreUrl');
    expect(raw).not.toContain('http://');
  });

  it('physically purges legacy coreUrl from storage on successful load', () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        completed: true,
        workspacePath: 'C:/Projects/Bolt',
        coreUrl: 'https://attacker.example',
        lastRunId: 'run_legacy',
      }),
    );

    const session = loadDesktopSession();

    expect(session).toEqual({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_legacy',
    });
    expect(session).not.toHaveProperty('coreUrl');
    const raw = localStorage.getItem(SESSION_KEY) ?? '';
    expect(raw).not.toContain('coreUrl');
    expect(raw).not.toContain('attacker.example');
  });

  it('does not expose coreUrl in memory when migration write fails', () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function setItem(key: string, value: string) {
      if (key === SESSION_KEY && value.includes('"completed":true')) {
        throw new Error('quota exceeded');
      }
      return original.call(this, key, value);
    };
    try {
      localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({
          completed: true,
          workspacePath: 'C:/Projects/Bolt',
          coreUrl: 'https://attacker.example',
          lastRunId: 'run_legacy',
        }),
      );
      // reload path uses getItem only first; force parse path:
      const session = loadDesktopSession();
      expect(session).not.toHaveProperty('coreUrl');
      expect(JSON.stringify(session)).not.toContain('attacker.example');
    } finally {
      Storage.prototype.setItem = original;
    }
  });

  it('recovers defaults from corrupted storage', () => {
    localStorage.setItem(SESSION_KEY, '{bad');
    expect(loadDesktopSession().completed).toBe(false);
  });
});
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/desktopSession.test.ts
```

Expected: FAIL because `coreUrl` still exists / is still returned / not purged.

- [ ] **Step 3: Minimal implementation**

Replace `apps/desktop/src/desktopSession.ts` with:

```ts
export interface DesktopSession {
  completed: boolean;
  workspacePath: string;
  lastRunId: string | null;
}

export const SESSION_KEY = 'bolt.desktop.session';

const defaults: DesktopSession = {
  completed: false,
  workspacePath: '',
  lastRunId: null,
};

export function loadDesktopSession(storage: Storage = localStorage): DesktopSession {
  const raw = storage.getItem(SESSION_KEY);
  if (!raw) return { ...defaults };
  try {
    const parsed = JSON.parse(raw) as unknown;
    const session = normalize(parsed);
    if (hasLegacyCoreUrl(parsed)) {
      try {
        saveDesktopSession(session, storage);
      } catch {
        // Migration write failure must not block startup or re-expose the old value.
      }
    }
    return session;
  } catch {
    return { ...defaults };
  }
}

export function saveDesktopSession(session: DesktopSession, storage: Storage = localStorage): void {
  const safe: DesktopSession = {
    completed: session.completed === true,
    workspacePath: typeof session.workspacePath === 'string' ? session.workspacePath : '',
    lastRunId: typeof session.lastRunId === 'string' ? session.lastRunId : null,
  };
  storage.setItem(SESSION_KEY, JSON.stringify(safe));
}

function normalize(value: unknown): DesktopSession {
  if (!isRecord(value)) return { ...defaults };
  return {
    completed: value.completed === true,
    workspacePath: typeof value.workspacePath === 'string' ? value.workspacePath : '',
    lastRunId: typeof value.lastRunId === 'string' ? value.lastRunId : null,
  };
}

function hasLegacyCoreUrl(value: unknown): boolean {
  return isRecord(value) && Object.prototype.hasOwnProperty.call(value, 'coreUrl');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
```

- [ ] **Step 4: Run GREEN**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/desktopSession.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/desktop/src/desktopSession.ts apps/desktop/src/desktopSession.test.ts
git commit -m "feat(desktop): purge coreUrl from desktop session storage"
```

---

### Task 2: Transport accepts only relative paths

**Files:**
- Modify: `apps/desktop/src/agentCoreAuth.ts`
- Modify: `apps/desktop/src/agentCoreAuth.test.ts`

- [ ] **Step 1: Write failing transport tests**

Add to `apps/desktop/src/agentCoreAuth.test.ts`:

```ts
  it('rejects absolute Agent Core URLs before any bridge call', () => {
    const agentCoreRequest = vi.fn();
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreRequest,
    };

    expect(() => createAgentCoreTransport()('http://127.0.0.1:8000/health')).toThrow('CORE_REQUEST_INVALID');
    expect(() => createAgentCoreTransport()('//evil.example/health')).toThrow('CORE_REQUEST_INVALID');
    expect(() => createAgentCoreTransport()('http://user:pass@127.0.0.1/health')).toThrow('CORE_REQUEST_INVALID');
    expect(() => createAgentCoreTransport()('/health#frag')).toThrow('CORE_REQUEST_INVALID');
    expect(() => createAgentCoreTransport()('\\health')).toThrow('CORE_REQUEST_INVALID');
    expect(agentCoreRequest).not.toHaveBeenCalled();
  });

  it('accepts relative path input only', () => {
    const agentCoreRequest = vi.fn().mockReturnValue({
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      response: Promise.resolve({
        requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
        generationId: 'generation-1',
        status: 200,
        statusText: 'OK',
        headers: [['content-type', 'application/json']],
        body: '{}',
      }),
      cancel: vi.fn().mockResolvedValue('already_finished'),
    });
    window.bolt = { selectWorkspace: vi.fn(), agentCoreRequest };

    createAgentCoreTransport()('/health', { method: 'GET' });

    expect(agentCoreRequest).toHaveBeenCalledWith('/health', { method: 'GET' });
  });
```

Keep existing relative-path tests; remove any expectation that absolute URLs are rewritten.

- [ ] **Step 2: Run RED**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/agentCoreAuth.test.ts
```

Expected: FAIL because absolute URLs are currently passed through.

- [ ] **Step 3: Minimal implementation**

Update `createAgentCoreTransport` in `apps/desktop/src/agentCoreAuth.ts`:

```ts
export function createAgentCoreTransport(): AgentCoreTransport {
  return (input: string, init?: RequestInit) => {
    const path = assertRelativeAgentCorePath(input);
    const bridge = typeof window === 'undefined' ? undefined : window.bolt?.agentCoreRequest;
    if (!bridge) {
      throw new Error('Bolt Desktop Agent Core bridge 不可用');
    }

    const handle = bridge(path, serializeRequestInit(init));
    return {
      requestId: handle.requestId,
      response: handle.response.then(toResponse),
      cancel: handle.cancel,
    };
  };
}

function assertRelativeAgentCorePath(input: string): string {
  if (typeof input !== 'string' || input.length === 0) {
    throw new Error('CORE_REQUEST_INVALID');
  }
  if (
    !input.startsWith('/')
    || input.startsWith('//')
    || input.includes('\\')
    || input.includes('#')
    || input.includes('://')
    || input.includes('@')
  ) {
    throw new Error('CORE_REQUEST_INVALID');
  }
  return input;
}
```

Do **not** parse absolute URLs and extract path/query.

- [ ] **Step 4: Run GREEN**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/agentCoreAuth.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/desktop/src/agentCoreAuth.ts apps/desktop/src/agentCoreAuth.test.ts
git commit -m "fix(desktop): reject absolute Agent Core URLs in transport"
```

---

### Task 3: Path-only core/harness/workflow clients

**Files:**
- Modify: `apps/desktop/src/coreClient.ts`
- Modify: `apps/desktop/src/harnessClient.ts`
- Modify: `apps/desktop/src/harnessClientAutonomy.ts`
- Modify: `apps/desktop/src/workflowClient.ts`
- Modify: `apps/desktop/src/coreClient.test.ts` (if present) / `apps/desktop/src/harnessClient.test.ts`
- Modify: `apps/desktop/src/harnessClientAutonomy.test.ts`

- [ ] **Step 1: Write failing client contract tests**

In `apps/desktop/src/harnessClient.test.ts`, change expectations to relative paths and remove `baseUrl` args. Example pattern:

```ts
it('creates a harness run with relative path only', async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: 'run_1', goal: 'g', workspace: 'C:/w' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );

  await createHarnessRun('build feature', 'C:/w', fetcher);

  expect(fetcher).toHaveBeenCalledWith('/harness/runs', expect.objectContaining({ method: 'POST' }));
  const body = JSON.parse(String(fetcher.mock.calls[0][1].body));
  expect(body).toEqual({ goal: 'build feature', workspace: 'C:/w' });
});
```

Add one autonomy test in `harnessClientAutonomy.test.ts`:

```ts
it('creates a goal without baseUrl', async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: 'goal_1' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
  await createGoal({ objective: 'x' }, fetcher);
  expect(fetcher).toHaveBeenCalledWith('/goals', expect.objectContaining({ method: 'POST' }));
});
```

Update `coreClient` test / add:

```ts
it('checks health via /health', async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ status: 'ok', service: 'bolt-agent-core' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
  await expect(fetchCoreHealth(fetcher)).resolves.toBe('ok');
  expect(fetcher).toHaveBeenCalledWith('/health');
});
```

- [ ] **Step 2: Run RED**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/harnessClient.test.ts src/harnessClientAutonomy.test.ts src/coreClient.test.ts
```

Expected: FAIL on arity / absolute URL expectations.

- [ ] **Step 3: Mechanical path-only rewrite**

Transform every exported client function with this rule:

```ts
// before
export async function createHarnessRun(baseUrl: string, goal: string, workspace: string, fetcher: Fetcher) {
  return readJson(await fetcher(`${baseUrl}/harness/runs`, jsonPost({ goal, workspace })));
}

// after
export async function createHarnessRun(goal: string, workspace: string, fetcher: Fetcher) {
  return readJson(await fetcher('/harness/runs', jsonPost({ goal, workspace })));
}
```

Apply to **all** functions in:

- `coreClient.ts`
- `harnessClient.ts`
- `harnessClientAutonomy.ts`
- `workflowClient.ts`

Rules:

1. Delete the first `baseUrl: string` parameter everywhere it meant Agent Core.
2. Replace `` `${baseUrl}/...` `` with `'/...'`.
3. Keep provider model field `base_url` untouched inside payloads.
4. Keep function names and return types unchanged.

For `workflowClient.ts`, mirror the same arity change and delegate to path-only harness helpers.

- [ ] **Step 4: Run focused GREEN**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/harnessClient.test.ts src/harnessClientAutonomy.test.ts src/coreClient.test.ts
```

Expected: PASS for these files. Broader panel compile/test failures are expected until Task 4.

- [ ] **Step 5: Commit**

```bash
git add apps/desktop/src/coreClient.ts apps/desktop/src/harnessClient.ts apps/desktop/src/harnessClientAutonomy.ts apps/desktop/src/workflowClient.ts apps/desktop/src/harnessClient.test.ts apps/desktop/src/harnessClientAutonomy.test.ts apps/desktop/src/coreClient.test.ts
git commit -m "feat(desktop): make Agent Core clients path-only"
```

---

### Task 4: panelsApi + all panels drop Agent Core `baseUrl`

**Files:**
- Modify: `apps/desktop/src/panelsApi.ts`
- Modify: `apps/desktop/src/PanelsSection.tsx`
- Modify: every production panel listed below
- Modify: corresponding panel tests

Production panels that currently take Agent Core `baseUrl` (must all be cleaned):

```text
AuditTimelinePanel.tsx
AutoContinuePanel.tsx
AutoFixPanel.tsx
AutonomousLoopPanel.tsx
BuilderPanel.tsx
CheckpointPanel.tsx
DesktopBetaShipPanel.tsx
DiagnosticsCenterPanel.tsx
ExecutionHandoffPanel.tsx
ExecutionQueuePanel.tsx
FailureExplanationPanel.tsx
GateFreezePanel.tsx
GoalConsole.tsx
MemorySearchPanel.tsx
MultiAgentStatusPanel.tsx
MultiTaskQueuePanel.tsx
OrchestratorPanel.tsx
PermissionCenterPanel.tsx
ProductWorkbenchPanel.tsx
ReleaseReadinessPanel.tsx
ResearcherPanel.tsx
ReviewerPanel.tsx
SessionRecoveryPanel.tsx
SettingsToolsPanel.tsx
SideChatPanel.tsx
SkillLearnerPanel.tsx
SleepWakePanel.tsx
TaskClosurePanel.tsx
TaskHomePanel.tsx
TestRunnerPanel.tsx
ToolVerificationPanel.tsx
```

- [ ] **Step 1: Write one representative RED for panel API shape**

In `apps/desktop/src/SideChatPanel.test.tsx` (create if missing) or update existing:

```ts
it('steers the current run without a baseUrl argument', async () => {
  const steerRun = vi.fn().mockResolvedValue({ status: 'accepted' });
  render(<SideChatPanel runId="run_1" api={{ steerRun }} />);
  await userEvent.type(screen.getByLabelText('侧聊内容'), '继续');
  await userEvent.click(screen.getByRole('button', { name: '发送指令' }));
  expect(steerRun).toHaveBeenCalledWith('run_1', '继续');
});
```

Also update one `panelsApi` consumer expectation if covered by `PanelsSection.test.tsx`: panels render without `baseUrl` prop.

- [ ] **Step 2: Run RED**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/SideChatPanel.test.tsx src/PanelsSection.test.tsx
```

Expected: FAIL on old arity / missing props.

- [ ] **Step 3: Rewrite panelsApi**

Change bound API methods from:

```ts
createCheckpoint: (url: string, p: Record<string, unknown>) => createCheckpoint(url, p, fetcher)
```

to:

```ts
createCheckpoint: (p: Record<string, unknown>) => createCheckpoint(p, fetcher)
```

Apply to every method in `createPanelsApi`.

Update `PanelsApi` / local panel API interfaces so **no method takes an Agent Core URL first argument**.

- [ ] **Step 4: Rewrite panels and PanelsSection**

For each panel:

```ts
// before
export function SideChatPanel({ runId, api, baseUrl = 'http://core' }: SideChatPanelProps) {
  await api.steerRun(baseUrl, runId, content);
}

// after
export function SideChatPanel({ runId, api }: SideChatPanelProps) {
  await api.steerRun(runId, content);
}
```

Hard rules:

1. Delete prop `baseUrl?: string` when it means Agent Core.
2. Delete defaults like `baseUrl = 'http://core'`.
3. Delete `baseUrl={baseUrl}` in `PanelsSection.tsx`.
4. Delete `baseUrl` from `PanelsProps`.
5. If a panel currently calls client functions directly with `baseUrl`, switch to path-only client arity.
6. Do not rename provider model `base_url`.

- [ ] **Step 5: Update panel unit tests mechanically**

In every `*.test.tsx` under `apps/desktop/src`:

1. Remove `baseUrl="http://test"` / `baseUrl="http://core"` props.
2. Change mocked API signatures to drop the URL argument.
3. Expect relative paths if the test asserts fetcher calls.

Example:

```ts
// before
await api.fetchStatus('http://test');
expect(fetcher).toHaveBeenCalledWith('http://test/auto-continue/status');

// after
await api.fetchStatus();
expect(fetcher).toHaveBeenCalledWith('/auto-continue/status');
```

- [ ] **Step 6: Run panel-focused GREEN batches**

Run in batches to keep feedback tight:

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/SideChatPanel.test.tsx src/GoalConsole.test.tsx src/CheckpointPanel.test.tsx src/PanelsSection.test.tsx
pnpm.cmd --filter @bolt/desktop exec vitest run src/TaskClosurePanel.test.tsx src/ExecutionQueuePanel.test.tsx src/ExecutionHandoffPanel.test.tsx src/PermissionCenterPanel.test.tsx
pnpm.cmd --filter @bolt/desktop exec vitest run src/AutoContinuePanel.test.tsx src/SkillLearnerPanel.test.tsx src/ToolVerificationPanel.test.tsx src/AutonomousLoopPanel.test.tsx
```

Expected: those batches PASS. Continue until all panel unit tests listed in the file map pass.

- [ ] **Step 7: Commit**

```bash
git add apps/desktop/src/panelsApi.ts apps/desktop/src/PanelsSection.tsx apps/desktop/src/*Panel*.tsx apps/desktop/src/GoalConsole.tsx apps/desktop/src/*Panel*.test.tsx apps/desktop/src/GoalConsole.test.tsx apps/desktop/src/PanelsSection.test.tsx
git commit -m "feat(desktop): remove Agent Core baseUrl from panels and panelsApi"
```

---

### Task 5: App + LiquidGlass managed Core UI and error copy

**Files:**
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/LiquidGlassTypes.ts`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.tsx`
- Modify: `apps/desktop/src/LiquidGlassSettings.tsx`
- Modify: `apps/desktop/src/LiquidGlassSettingsData.tsx` (and surfaces file if present)
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/LiquidGlassWorkbench.test.tsx`

- [ ] **Step 1: Write failing UI/copy tests**

In `App.test.tsx` / settings-related test, assert:

```ts
it('shows managed local Agent Core status instead of an editable URL', async () => {
  localStorage.setItem(
    'bolt.desktop.session',
    JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', lastRunId: null }),
  );
  const fetcher = vi.fn().mockImplementation(async (input: string) => {
    if (input === '/health') {
      return new Response(JSON.stringify({ status: 'ok', service: 'bolt-agent-core' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }
    if (input === '/desktop/settings') {
      return new Response(JSON.stringify({
        theme: 'dark',
        language: 'zh-CN',
        default_workspace: '',
        has_api_key: false,
        credential_revision: 0,
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    if (input === '/goals/unfinished') {
      return new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } });
    }
    return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
  });

  render(<App fetcher={fetcher} />);

  expect(screen.queryByLabelText('核心服务地址')).not.toBeInTheDocument();
  // open settings if needed in current shell
  expect(await screen.findByText('本地 Agent Core · 由 Bolt 自动管理')).toBeInTheDocument();
});
```

Also assert the new memory-refresh error path text appears when `/memory` fails, if covered.

Update `LiquidGlassWorkbench.test.tsx` props to remove `coreUrl`.

- [ ] **Step 2: Run RED**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/App.test.tsx src/LiquidGlassWorkbench.test.tsx
```

Expected: FAIL on missing managed copy / old coreUrl props.

- [ ] **Step 3: Implement App path-only wiring + copy**

In `App.tsx`:

1. Remove all `session.coreUrl` usages.
2. Call path-only clients:

```ts
fetchCoreHealth(fetcher)
fetchUnfinishedGoals(fetcher)
loadDesktopSettings(fetcher)
startWorkflowRun(goal, workspace, fetcher)
```

3. Replace error text:

```ts
'无法连接本地 Agent Core。请确认 Bolt 桌面端已启动核心服务。'
```

4. First-run completion object no longer includes `coreUrl`.
5. `PanelsSection` no longer receives `baseUrl`.
6. Workbench props: delete `coreUrl`; keep `coreStatus`.

In settings data/UI, add a read-only row/metric under general:

```ts
{
  title: '本地 Agent Core',
  detail: '由 Bolt 桌面端自动管理，用户不可配置地址。',
  control: '本地 Agent Core · 由 Bolt 自动管理',
  tone: 'success',
}
```

Workbench continues to show only `本地` / `离线` from `coreStatus`.

- [ ] **Step 4: Run GREEN focused**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/App.test.tsx src/LiquidGlassWorkbench.test.tsx src/desktopSession.test.ts src/agentCoreAuth.test.ts
```

Expected: PASS or only remaining failures are dogfood files handled in Task 7.

- [ ] **Step 5: Commit**

```bash
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/LiquidGlassTypes.ts apps/desktop/src/LiquidGlassWorkbench.tsx apps/desktop/src/LiquidGlassWorkbench.test.tsx apps/desktop/src/LiquidGlassSettings.tsx apps/desktop/src/LiquidGlassSettingsData.tsx
git commit -m "feat(desktop): show managed Agent Core status without URL controls"
```

---

### Task 6: Static architecture gate for residual Core URL authority

**Files:**
- Modify: `scripts/check-architecture.mjs`
- Optional test evidence via command output only

- [ ] **Step 1: Write the failing gate expectation by introducing the check first**

Add to `checkP0LocalSecurity` in `scripts/check-architecture.mjs`:

```js
  if (rel.startsWith('apps/desktop/src/') && !rel.includes('.test.') && !rel.endsWith('.test.ts') && !rel.endsWith('.test.tsx')) {
    if (/\bcoreUrl\b/.test(text)) fail(rel, 'Renderer must not retain coreUrl');
    if (/\bDEFAULT_CORE_URL\b/.test(text)) fail(rel, 'DEFAULT_CORE_URL is forbidden');
    if (/\bhttp:\/\/core\b/.test(text)) fail(rel, 'http://core defaults are forbidden');
    if (/\bagentCoreEndpoint\b/.test(text)) fail(rel, 'agentCoreEndpoint must not reappear in Renderer');
    // Agent Core baseUrl props/params are forbidden. Provider model field base_url is allowed.
    if (/\bbaseUrl\b/.test(text)) fail(rel, 'Agent Core baseUrl parameter/prop is forbidden in production Renderer sources');
  }
```

If provider docs/UI strings cause false positives on `baseUrl`, keep the identifier ban on `baseUrl` camelCase only; `base_url` remains allowed for model provider config.

- [ ] **Step 2: Run RED if residues remain**

```powershell
node scripts/check-architecture.mjs
```

Expected before full cleanup: FAIL listing residual files. After Tasks 1–5 complete, this should pass. If Task 6 is implemented before cleanup finishes, use the failure list as the remaining work queue.

- [ ] **Step 3: Ensure production sources pass the gate**

Fix any remaining production residues the gate reports. Do not whitelist panel files.

- [ ] **Step 4: Run GREEN**

```powershell
node scripts/check-architecture.mjs
```

Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add scripts/check-architecture.mjs
git commit -m "test(arch): forbid residual Agent Core URL authority in Renderer"
```

---

### Task 7: Align App/dogfood tests to current shell and path-only APIs

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/uiWorkflowDogfood.test.tsx`
- Modify: `apps/desktop/src/taskClosureDogfood.test.tsx`
- Modify: `apps/desktop/src/taskClosureAssessmentDogfood.test.tsx`
- Modify: any remaining failing Desktop tests from full run

- [ ] **Step 1: Rewrite dogfood/session fixtures**

Replace every:

```ts
JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' })
```

with:

```ts
JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', lastRunId: null })
```

Replace fetcher expectations:

```ts
// before
expect(fetcher).toHaveBeenCalledWith('http://core/health')
// after
expect(fetcher).toHaveBeenCalledWith('/health')
```

- [ ] **Step 2: Rewrite UI assertions to current LiquidGlass shell**

Remove assertions for deleted controls:

- `核心服务地址`
- old English leftovers already covered
- old button names that no longer exist in the shell

Keep real business intent with current labels/roles available in the shell, for example:

- workspace selection still works
- health becomes offline/local according to `/health`
- no editable Core URL
- managed Core copy visible from settings entry points used by the shell
- permission / run / memory flows still call relative paths

If a dogfood test depended on a removed panel chrome, retarget it to the current entry that still exercises the same backend path.

- [ ] **Step 3: Run the previously red suite**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/App.test.tsx src/uiWorkflowDogfood.test.tsx src/AutoContinuePanel.test.tsx src/SkillLearnerPanel.test.tsx src/taskClosureDogfood.test.tsx src/taskClosureAssessmentDogfood.test.tsx
```

Expected: PASS

Anti-cheat rules while fixing:

1. No `it.skip` / `describe.skip` / `it.only` / `test.todo` added to hide failures.
2. No deleted real business assertions without replacement coverage.
3. No weakened matchers that no longer prove the behavior.

- [ ] **Step 4: Commit**

```bash
git add apps/desktop/src/App.test.tsx apps/desktop/src/uiWorkflowDogfood.test.tsx apps/desktop/src/taskClosureDogfood.test.tsx apps/desktop/src/taskClosureAssessmentDogfood.test.tsx apps/desktop/src/AutoContinuePanel.test.tsx apps/desktop/src/SkillLearnerPanel.test.tsx
git commit -m "test(desktop): align dogfood and App tests to path-only managed Core UI"
```

---

### Task 8: Joint verification and release-status handoff

**Files:**
- Evidence only; modify code only if a regression is proven in-scope

- [ ] **Step 1: Run Desktop P0 focused suite**

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/desktopSession.test.ts src/harnessClient.test.ts src/LiquidGlassSettingsCredential.test.tsx src/agentCoreAuth.test.ts electron/agentCoreAuth.test.ts electron/preloadBridge.test.ts electron/mainSecurity.test.ts electron/agentCoreRuntime.test.ts electron/agentCoreReadiness.test.ts electron/agentCoreIpc.test.ts electron/desktopStartup.test.ts electron/electronBridge.integration.test.ts
```

Expected: all PASS

- [ ] **Step 2: Run full Desktop suite**

```powershell
pnpm.cmd --filter @bolt/desktop test -- --run
```

Expected: exit 0, zero failed tests, no new skips

- [ ] **Step 3: Static + build**

```powershell
node scripts/check-architecture.mjs
pnpm.cmd --filter @bolt/desktop build
git diff --check
```

Expected: all exit 0

- [ ] **Step 4: Residual scan evidence**

```powershell
rg -n "coreUrl|DEFAULT_CORE_URL|http://core|agentCoreEndpoint" apps/desktop/src --glob "!*.test.*"
rg -n "\bbaseUrl\b" apps/desktop/src --glob "!*.test.*"
```

Expected:

- no `coreUrl` / `DEFAULT_CORE_URL` / `http://core` / `agentCoreEndpoint` in production sources
- no camelCase Agent Core `baseUrl`
- provider `base_url` may remain

- [ ] **Step 5: Final handoff text must include**

1. What completed
2. Files changed
3. Exact commands + real results
4. Whether Desktop full suite is green
5. Any failures with root cause classification
6. 8-dim review with 🔴/🟡/🟢
7. Release decision table:
   - local dev: allow
   - team verification: allow
   - player beta: still blocked
   - public beta: still blocked
8. Next highest priority: Windows packaging/signing/update/crash evidence slice

Do **not** claim player release readiness.

---

## Spec coverage self-check

| Spec requirement | Task |
|------------------|------|
| Delete `coreUrl` from session type | Task 1 |
| Physical purge of legacy `coreUrl` | Task 1 |
| Migration write failure does not re-expose value | Task 1 |
| Path-only clients | Task 3 |
| No absolute URL compatibility extraction | Task 2 |
| Absolute URL => `CORE_REQUEST_INVALID`, zero bridge calls | Task 2 |
| Settings read-only managed Core copy | Task 5 |
| Workbench health only | Task 5 |
| Error copy update | Task 5 |
| Clean all residual panels / `http://core` defaults | Task 4 |
| Static acceptance gate | Task 6 |
| Desktop full green without skip cheating | Task 7 + Task 8 |
| Keep P0 intact / no player-beta claim | Task 8 |

## Placeholder / consistency scan

- No TBD/TODO steps.
- Client arity rule is consistent: drop Agent Core URL arg, keep business args + fetcher.
- Provider `base_url` intentionally retained and distinguished from Agent Core `baseUrl`.
- Transport fail-closed behavior matches P0: no path extraction from absolute URLs.
