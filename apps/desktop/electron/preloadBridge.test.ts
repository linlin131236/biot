import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import ts from 'typescript';
import { describe, expect, it, vi } from 'vitest';

const electron = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
}));

vi.mock('electron', () => ({
  contextBridge: { exposeInMainWorld: electron.exposeInMainWorld },
  ipcRenderer: { invoke: electron.invoke },
}));

type Bridge = {
  selectWorkspace: () => Promise<string | null>;
  agentCoreRequest: (
    input: string,
    init?: { method?: string; headers?: [string, string][]; body?: string },
  ) => {
    requestId: string;
    response: Promise<unknown>;
    cancel: () => Promise<'cancelled' | 'already_finished'>;
  };
  diagnostics: {
    exportSummary: () => Promise<string>;
    openDir: () => Promise<void>;
    setEnabled: (enabled: boolean) => Promise<boolean>;
    getEnabled: () => Promise<boolean>;
    record: (payload: { component: string; message: string; details?: Record<string, unknown> }) => Promise<unknown>;
  };
  update: {
    status: () => Promise<Record<string, unknown>>;
    check: (manifestUrl?: string) => Promise<Record<string, unknown>>;
  };
};

async function loadBridge() {
  electron.exposeInMainWorld.mockReset();
  electron.invoke.mockReset();
  const source = readFileSync(join(__dirname, 'preload.cts'), 'utf-8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const requireMock = (id: string) => {
    if (id !== 'electron') throw new Error(`Unexpected preload dependency: ${id}`);
    return {
      contextBridge: { exposeInMainWorld: electron.exposeInMainWorld },
      ipcRenderer: { invoke: electron.invoke },
    };
  };
  new Function('require', 'module', 'exports', compiled)(requireMock, { exports: {} }, {});
  return electron.exposeInMainWorld.mock.calls[0][1] as Bridge;
}

describe('preload Agent Core DTO facade', () => {
  it('exposes no endpoint, token, fetch, or raw ipcRenderer capability', async () => {
    const bridge = await loadBridge();

    expect(Object.keys(bridge).sort()).toEqual(['agentCoreRequest', 'diagnostics', 'selectWorkspace', 'update'].sort());
    expect(bridge).not.toHaveProperty('agentCoreEndpoint');
    expect(bridge).not.toHaveProperty('agentCoreFetch');
    expect(bridge).not.toHaveProperty('ipcRenderer');
    expect(Object.keys(bridge.diagnostics).sort()).toEqual(['exportSummary', 'getEnabled', 'openDir', 'record', 'setEnabled'].sort());
    expect(Object.keys(bridge.update).sort()).toEqual(['check', 'status'].sort());
    // Narrow surfaces only: no raw invoke/fetch/token/endpoint on nested facades.
    expect(bridge.diagnostics).not.toHaveProperty('invoke');
    expect(bridge.update).not.toHaveProperty('invoke');
    expect(bridge.diagnostics).not.toHaveProperty('fetch');
    expect(bridge.update).not.toHaveProperty('fetch');
  });

  it('routes diagnostics and update through fixed channels only', async () => {
    const bridge = await loadBridge();
    electron.invoke.mockResolvedValue('ok');
    await bridge.diagnostics.exportSummary();
    await bridge.diagnostics.openDir();
    await bridge.diagnostics.setEnabled(false);
    await bridge.diagnostics.getEnabled();
    await bridge.diagnostics.record({ component: 'renderer', message: 'boom' });
    await bridge.update.status();
    await bridge.update.check('https://updates.bolt.local/m.json');
    const channels = electron.invoke.mock.calls.map((call) => call[0]);
    expect(channels).toEqual([
      'bolt:diagnostics:export-summary',
      'bolt:diagnostics:open-dir',
      'bolt:diagnostics:set-enabled',
      'bolt:diagnostics:get-enabled',
      'bolt:diagnostics:record',
      'bolt:update:status',
      'bolt:update:check',
    ]);
    // No generic invoke API is exposed on the bridge itself.
    expect(bridge).not.toHaveProperty('invoke');
  });

  it('returns the request handle synchronously and invokes request and cancel channels', async () => {
    vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e');
    const bridge = await loadBridge();
    electron.invoke.mockResolvedValueOnce({
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      generationId: 'generation-1',
      status: 200,
      statusText: 'OK',
      headers: [['content-type', 'application/json']],
      body: '{}',
    });
    electron.invoke.mockResolvedValueOnce('cancelled');

    const handle = bridge.agentCoreRequest('/memory', { method: 'GET' });

    expect(handle.requestId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(handle.response).toBeInstanceOf(Promise);
    expect(electron.invoke).toHaveBeenCalledWith('bolt:agent-core:request', {
      requestId: handle.requestId,
      path: '/memory',
      method: 'GET',
      headers: undefined,
      body: undefined,
    });
    await handle.response;
    await expect(handle.cancel()).resolves.toBe('cancelled');
    expect(electron.invoke).toHaveBeenLastCalledWith('bolt:agent-core:cancel', {
      requestId: handle.requestId,
    });
  });
});
