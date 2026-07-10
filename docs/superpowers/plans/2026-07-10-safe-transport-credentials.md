# Safe Transport and Credentials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关闭 Renderer 到非受信 Agent Core 的网络回退，并用 Windows DPAPI 建立可迁移、可测试的模型凭据存储。

**Architecture:** Renderer 只调用窄 `AgentCoreTransport`；preload 校验 loopback endpoint 并附加 Electron 持有的 Token。Python 使用 `CredentialStore` interface，生产 adapter 调用 Windows DPAPI，测试 adapter 保存在内存；旧 `.bolt/desktop-api-key` 只在原子迁移中读取。

**Tech Stack:** Electron preload、TypeScript、Vitest、Python Protocol、ctypes/Windows DPAPI、pytest。

---

### Task 1: Fail-closed Renderer transport

**Files:**
- Modify: `apps/desktop/src/agentCoreAuth.ts:1-45`
- Modify: `apps/desktop/src/agentCoreAuth.test.ts:1-62`
- Modify if needed: `apps/desktop/src/vite-env.d.ts`

- [ ] **Step 1: Replace fallback expectations with failing rejection tests**

Add tests equivalent to:

```ts
it.each([
  'https://example.com/memory',
  'http://127.0.0.1:9000/memory',
  'file:///tmp/secret',
])('rejects an untrusted Agent Core URL: %s', async (url) => {
  window.bolt = {
    selectWorkspace: vi.fn(),
    agentCoreEndpoint: vi.fn().mockResolvedValue({ port: 8000 }),
    agentCoreFetch: vi.fn(),
  };
  const networkFetch = vi.fn();

  await expect(createAgentCoreFetcher(networkFetch)(url)).rejects.toThrow('不受信任');
  expect(networkFetch).not.toHaveBeenCalled();
  expect(window.bolt.agentCoreFetch).not.toHaveBeenCalled();
});
```

Also add a test that throws when `window.bolt.agentCoreFetch` is unavailable instead of using browser fetch.

- [ ] **Step 2: Run the tests and verify red**

Run:

```bash
pnpm --filter @bolt/desktop test -- agentCoreAuth.test.ts
```

Expected: external and wrong-port cases fail because the current implementation calls the injected fallback fetcher.

- [ ] **Step 3: Implement the minimal fail-closed fetcher**

Change the production path to:

```ts
export function createAgentCoreFetcher(): Fetcher {
  return async (input, init) => {
    const endpoint = await readAgentCoreEndpoint();
    if (!isTrustedAgentCoreUrl(input, endpoint.port)) {
      throw new Error('拒绝不受信任的 Agent Core 地址');
    }
    if (typeof window === 'undefined' || !window.bolt?.agentCoreFetch) {
      throw new Error('Bolt Desktop Agent Core bridge 不可用');
    }
    const response = await window.bolt.agentCoreFetch(input, serializeRequestInit(init));
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  };
}
```

Tests needing a transport must inject their own explicit mock into the higher-level client rather than keeping a production fallback parameter.

- [ ] **Step 4: Run focused Desktop tests**

Run:

```bash
pnpm --filter @bolt/desktop test -- agentCoreAuth.test.ts
```

Expected: all agentCoreAuth tests pass and no fallback fetch is called.

- [ ] **Step 5: Commit only these files**

```bash
git add apps/desktop/src/agentCoreAuth.ts apps/desktop/src/agentCoreAuth.test.ts apps/desktop/src/vite-env.d.ts
git commit -m "fix: fail closed on untrusted agent core urls"
```

Do not stage unrelated existing UI changes.

### Task 2: Keep endpoint and token inside the Desktop bridge

**Files:**
- Modify: `apps/desktop/electron/preload.ts:9-74`
- Modify: `apps/desktop/electron/preload.cts` only after comparing it with `preload.ts`; preserve the packaging source of truth chosen by `tsconfig.electron.json`
- Modify: `apps/desktop/electron/preloadBridge.test.ts`
- Modify: `apps/desktop/electron/mainSecurity.test.ts`
- Verify: `apps/desktop/electron/main.ts:39-58`

- [ ] **Step 1: Add failing preload tests for token and URL confinement**

Add assertions that:

```ts
expect(exposedBridge).not.toHaveProperty('agentCoreAuth');
expect(exposedBridge).not.toHaveProperty('ipcRenderer');
expect(exposedBridge).not.toHaveProperty('invoke');
await expect(exposedBridge.agentCoreFetch('https://example.com')).rejects.toThrow();
```

Add a request test proving the bridge overwrites any renderer-supplied `authorization` header with its own token, rather than trusting the renderer:

```ts
expect(fetch).toHaveBeenCalledWith(
  'http://127.0.0.1:8000/healthz',
  expect.objectContaining({ headers: expect.any(Headers) }),
);
expect((fetch.mock.calls[0][1].headers as Headers).get('authorization'))
  .toBe('Bearer desktop-token');
```

- [ ] **Step 2: Run the tests and verify red**

```bash
pnpm --filter @bolt/desktop test -- preloadBridge.test.ts mainSecurity.test.ts
```

Expected: authorization override test fails because current code preserves a renderer-provided header.

- [ ] **Step 3: Make the bridge authoritative**

Use:

```ts
const headers = new Headers(init?.headers);
headers.delete('authorization');
if (!agentCoreToken) throw new Error('Agent Core 鉴权令牌不可用');
headers.set('authorization', `Bearer ${agentCoreToken}`);
```

Keep strict loopback host and exact port checks. Reject when the port environment value is absent or invalid in packaged mode; development may use explicit port `8000` only when the runtime has supplied it.

- [ ] **Step 4: Run preload and runtime tests**

```bash
pnpm --filter @bolt/desktop test -- preloadBridge.test.ts mainSecurity.test.ts agentCoreRuntime.test.ts
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit bridge changes**

```bash
git add apps/desktop/electron/preload.ts apps/desktop/electron/preload.cts apps/desktop/electron/preloadBridge.test.ts apps/desktop/electron/mainSecurity.test.ts
git commit -m "fix: keep agent core credentials inside desktop bridge"
```

Only stage `preload.cts` if it is confirmed as the current build source and the change is required.

### Task 3: Define the credential interface and in-memory adapter

**Files:**
- Create: `services/agent-core/src/bolt_core/credential_store.py`
- Create: `services/agent-core/tests/test_credential_store.py`

- [ ] **Step 1: Write failing contract tests**

```python
from bolt_core.credential_store import InMemoryCredentialStore


def test_in_memory_credentials_are_isolated_by_id():
    store = InMemoryCredentialStore()
    store.save("model.openai", "openai-secret")
    store.save("model.proxy", "proxy-secret")
    assert store.load("model.openai") == "openai-secret"
    assert store.load("model.proxy") == "proxy-secret"


def test_delete_removes_only_requested_credential():
    store = InMemoryCredentialStore({"a": "one", "b": "two"})
    store.delete("a")
    assert store.exists("a") is False
    assert store.load("b") == "two"
```

- [ ] **Step 2: Verify the tests fail**

```bash
cd services/agent-core && uv run pytest tests/test_credential_store.py -v
```

Expected: import failure because `credential_store.py` does not exist.

- [ ] **Step 3: Implement the interface and adapter**

```python
from typing import Protocol


class CredentialStore(Protocol):
    def save(self, credential_id: str, secret: str) -> None: ...
    def load(self, credential_id: str) -> str | None: ...
    def delete(self, credential_id: str) -> None: ...
    def exists(self, credential_id: str) -> bool: ...


class InMemoryCredentialStore:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = dict(values or {})

    def save(self, credential_id: str, secret: str) -> None:
        if not credential_id or not secret:
            raise ValueError("credential id and secret are required")
        self._values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        return self._values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self._values.pop(credential_id, None)

    def exists(self, credential_id: str) -> bool:
        return credential_id in self._values
```

- [ ] **Step 4: Run the credential tests**

```bash
cd services/agent-core && uv run pytest tests/test_credential_store.py -v
```

Expected: pass.

- [ ] **Step 5: Commit the interface**

```bash
git add services/agent-core/src/bolt_core/credential_store.py services/agent-core/tests/test_credential_store.py
git commit -m "feat: add model credential store interface"
```

### Task 4: Add the Windows DPAPI adapter

**Files:**
- Create: `services/agent-core/src/bolt_core/windows_dpapi.py`
- Create: `services/agent-core/src/bolt_core/windows_credential_store.py`
- Create: `services/agent-core/tests/test_windows_credential_store.py`
- Modify: `services/agent-core/pyproject.toml` only if an implementation dependency is demonstrably required; prefer stdlib `ctypes`

- [ ] **Step 1: Write failing adapter tests with an injected protector**

Avoid unit tests that depend on the host OS by injecting a protector:

```python
class FakeProtector:
    def protect(self, plaintext: bytes, entropy: bytes) -> bytes:
        return b"protected:" + entropy + b":" + plaintext

    def unprotect(self, ciphertext: bytes, entropy: bytes) -> bytes:
        prefix = b"protected:" + entropy + b":"
        assert ciphertext.startswith(prefix)
        return ciphertext[len(prefix):]


def test_windows_store_persists_only_ciphertext(tmp_path):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    store.save("model.openai", "sk-secret")
    assert store.load("model.openai") == "sk-secret"
    assert b"sk-secret" not in (tmp_path / "credentials" / "model.openai.bin").read_bytes()
```

Add tests for invalid credential IDs, replace-by-atomic-write and deletion.

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_windows_credential_store.py -v
```

Expected: import failure.

- [ ] **Step 3: Implement the DPAPI protector and file-backed adapter**

`windows_dpapi.py` must wrap `CryptProtectData`/`CryptUnprotectData` via `ctypes`, use current-user scope and a Bolt-specific entropy value. It must raise `CredentialProtectionError` with a stable non-secret message.

`windows_credential_store.py` must:

```python
SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")

class WindowsCredentialStore:
    def save(self, credential_id: str, secret: str) -> None:
        path = self._path_for(credential_id)
        ciphertext = self._protector.protect(
            secret.encode("utf-8"), self._entropy(credential_id)
        )
        atomic_write_bytes(path, ciphertext)
```

Use one file per credential under the Bolt user-data directory, never the project workspace. Atomic write uses sibling temp file, `os.replace`, and cleanup on failure.

- [ ] **Step 4: Run portable and Windows-only tests**

```bash
cd services/agent-core && uv run pytest tests/test_windows_credential_store.py -v
```

On Windows also run a marked real round-trip test:

```bash
cd services/agent-core && uv run pytest tests/test_windows_credential_store.py -v -m windows
```

Expected: fake protector tests pass everywhere; DPAPI round trip passes on Windows.

- [ ] **Step 5: Commit the DPAPI adapter**

```bash
git add services/agent-core/src/bolt_core/windows_dpapi.py services/agent-core/src/bolt_core/windows_credential_store.py services/agent-core/tests/test_windows_credential_store.py services/agent-core/pyproject.toml
git commit -m "feat: protect model credentials with windows dpapi"
```

### Task 5: Migrate the legacy plaintext key atomically

**Files:**
- Create: `services/agent-core/src/bolt_core/credential_migration.py`
- Create: `services/agent-core/tests/test_credential_migration.py`
- Modify: `services/agent-core/src/bolt_core/desktop_settings.py:34-96`
- Modify: `services/agent-core/tests/test_desktop_settings.py:51-85`

- [ ] **Step 1: Write migration failure and recovery tests**

```python
def test_migration_deletes_plaintext_only_after_verified_roundtrip(tmp_path):
    legacy = tmp_path / ".bolt" / "desktop-api-key"
    legacy.parent.mkdir()
    legacy.write_text("sk-legacy")
    store = InMemoryCredentialStore()

    result = migrate_legacy_api_key(legacy, store, "model.default")

    assert result.status == "migrated"
    assert store.load("model.default") == "sk-legacy"
    assert legacy.exists() is False


def test_migration_keeps_legacy_file_when_save_fails(tmp_path):
    legacy = write_legacy_key(tmp_path, "sk-legacy")
    store = FailingCredentialStore()
    result = migrate_legacy_api_key(legacy, store, "model.default")
    assert result.status == "failed"
    assert legacy.read_text() == "sk-legacy"
```

Add idempotency: if destination already contains the same secret, delete the legacy file and return `migrated`; if it contains a different secret, keep the legacy file and return `conflict`.

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_credential_migration.py tests/test_desktop_settings.py -v
```

Expected: migration module missing and old settings tests expect plaintext persistence.

- [ ] **Step 3: Implement migration and remove plaintext persistence from settings**

Expose:

```python
@dataclass(frozen=True)
class CredentialMigrationResult:
    status: Literal["absent", "migrated", "failed", "conflict"]
    error_code: str | None = None
```

`DesktopSettingsService` must no longer save, load or delete API keys. It may receive a `CredentialStore` only to report `has_api_key` for the default provider until provider registry replaces that status in the next sub-plan.

- [ ] **Step 4: Run focused backend tests**

```bash
cd services/agent-core && uv run pytest tests/test_credential_store.py tests/test_windows_credential_store.py tests/test_credential_migration.py tests/test_desktop_settings.py -v
```

Expected: all pass; no test asserts plaintext key file creation.

- [ ] **Step 5: Commit migration**

```bash
git add services/agent-core/src/bolt_core/credential_migration.py services/agent-core/src/bolt_core/desktop_settings.py services/agent-core/tests/test_credential_migration.py services/agent-core/tests/test_desktop_settings.py
git commit -m "fix: migrate legacy api keys out of plaintext storage"
```

### Task 6: Wire credentials into model settings and gateway

**Files:**
- Modify: `services/agent-core/src/bolt_core/model_settings.py:5-39`
- Modify: `services/agent-core/src/bolt_core/model_gateway.py:9-126`
- Modify: `services/agent-core/src/bolt_core/harness.py` at model settings construction and request creation
- Modify: `services/agent-core/src/bolt_core/app.py:113-145,284-290`
- Modify: `services/agent-core/tests/test_model_settings.py`
- Modify: `services/agent-core/tests/test_model_gateway.py`
- Modify: `services/agent-core/tests/test_app_model_gateway.py`

- [ ] **Step 1: Write failing tests proving restart-safe credential resolution**

```python
def test_model_settings_never_store_plaintext_key():
    credentials = InMemoryCredentialStore()
    store = ModelSettingsStore(credentials)
    status = store.update({"api_key": "sk-secret", "model": "gpt-test"})
    assert status.has_api_key is True
    assert not hasattr(store.config(), "api_key")
    assert credentials.load("model.default") == "sk-secret"


def test_gateway_resolves_credential_at_call_time():
    credentials = InMemoryCredentialStore({"model.default": "sk-secret"})
    config = ModelConfig(
        provider="openai-compatible",
        base_url="https://api.openai.com/v1",
        credential_id="model.default",
        model="gpt-test",
    )
    gateway = OpenAICompatibleGateway(credentials, client_factory=fake_client_factory)
    response = gateway.complete(ModelRequest([], config))
    assert response.status == "completed"
```

Also test deletion immediately causes `credential missing` and no cached key is used.

- [ ] **Step 2: Verify red**

```bash
cd services/agent-core && uv run pytest tests/test_model_settings.py tests/test_model_gateway.py tests/test_app_model_gateway.py -v
```

Expected: tests fail because `ModelConfig` stores `api_key` directly.

- [ ] **Step 3: Change model configuration to references**

Use:

```python
@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    credential_id: str | None
    model: str
    temperature: float = 0.2
    timeout: float = 120.0
```

`OpenAICompatibleGateway` receives `CredentialStore` and resolves `credential_id` immediately before constructing the OpenAI client. Fake provider remains credential-free. Error strings are stable codes such as `credential_missing`, `provider_timeout`, `provider_rate_limited`.

`create_app()` receives optional `credential_store`; production app creates `WindowsCredentialStore` from Electron-supplied `BOLT_USER_DATA`, tests inject memory store. Run legacy migration before constructing the harness.

- [ ] **Step 4: Run model and app tests**

```bash
cd services/agent-core && uv run pytest tests/test_model_settings.py tests/test_model_gateway.py tests/test_app_model_gateway.py tests/test_credential_migration.py -v
```

Expected: all pass and assertions confirm API keys do not appear in status payloads.

- [ ] **Step 5: Commit credential wiring**

```bash
git add services/agent-core/src/bolt_core/model_settings.py services/agent-core/src/bolt_core/model_gateway.py services/agent-core/src/bolt_core/harness.py services/agent-core/src/bolt_core/app.py services/agent-core/tests/test_model_settings.py services/agent-core/tests/test_model_gateway.py services/agent-core/tests/test_app_model_gateway.py
git commit -m "fix: resolve model credentials at call time"
```

### Task 7: Pass a stable user-data directory from Electron

**Files:**
- Modify: `apps/desktop/electron/main.ts:39-58`
- Modify: `apps/desktop/electron/agentCoreRuntime.ts`
- Modify: `apps/desktop/electron/agentCoreRuntime.test.ts`
- Modify: `services/agent-core/src/bolt_core/app.py:318-325`

- [ ] **Step 1: Add a failing runtime environment test**

```ts
expect(runtime.env.BOLT_USER_DATA).toBe('C:\\Users\\test\\AppData\\Roaming\\Bolt');
```

Pass `userDataPath` as an explicit input to `resolveAgentCoreRuntime` rather than reading Electron globals inside a pure resolver.

- [ ] **Step 2: Verify red**

```bash
pnpm --filter @bolt/desktop test -- agentCoreRuntime.test.ts
```

Expected: `BOLT_USER_DATA` is absent.

- [ ] **Step 3: Add the environment value**

In `main.ts` call:

```ts
resolveAgentCoreRuntime({
  ...,
  userDataPath: app.getPath('userData'),
});
```

Include `BOLT_USER_DATA` in the child environment. Python production startup rejects a missing user-data path when credential persistence is required; tests may inject a temporary path.

- [ ] **Step 4: Run runtime and backend startup tests**

```bash
pnpm --filter @bolt/desktop test -- agentCoreRuntime.test.ts
cd services/agent-core && uv run pytest tests/test_app_model_gateway.py tests/test_local_api_auth.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit runtime wiring**

```bash
git add apps/desktop/electron/main.ts apps/desktop/electron/agentCoreRuntime.ts apps/desktop/electron/agentCoreRuntime.test.ts services/agent-core/src/bolt_core/app.py
git commit -m "feat: bind credential storage to desktop user data"
```

### Task 8: Verify the first vertical slice

**Files:**
- Modify: `docs/SECURITY.md`
- Create: `docs/decisions/181-safe-agent-core-transport-and-credentials.md`

- [ ] **Step 1: Update security truth, removing stale fake-executor claims**

Document that real model/network calls exist, Core traffic is fail-closed, credentials use DPAPI, and write/shell permission behavior must be verified against the current Harness rather than the stale line claiming all approved requests use `FakeToolExecutor`.

- [ ] **Step 2: Record the decision**

The decision document must state the chosen seam, adapters, migration failure behavior and why browser fetch fallback is forbidden.

- [ ] **Step 3: Run the full slice verification**

```bash
pnpm --filter @bolt/desktop test -- agentCoreAuth.test.ts preloadBridge.test.ts mainSecurity.test.ts agentCoreRuntime.test.ts
cd services/agent-core && uv run pytest tests/test_credential_store.py tests/test_windows_credential_store.py tests/test_credential_migration.py tests/test_desktop_settings.py tests/test_model_settings.py tests/test_model_gateway.py tests/test_app_model_gateway.py tests/test_local_api_auth.py -v
```

Expected: all selected tests pass.

- [ ] **Step 4: Run size and architecture gates**

```bash
pnpm lint:size && pnpm lint:architecture && pnpm lint:boundaries
```

Expected: pass. If a file exceeds limits, split by responsibility; do not add a new size exception.

- [ ] **Step 5: Commit docs and gate evidence**

```bash
git add docs/SECURITY.md docs/decisions/181-safe-agent-core-transport-and-credentials.md
git commit -m "docs: record safe desktop transport and credential boundary"
```
