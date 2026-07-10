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

    expect(Object.keys(bridge)).toEqual(['selectWorkspace', 'agentCoreRequest']);
    expect(bridge).not.toHaveProperty('agentCoreEndpoint');
    expect(bridge).not.toHaveProperty('agentCoreFetch');
    expect(bridge).not.toHaveProperty('ipcRenderer');
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
