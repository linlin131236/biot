import { describe, expect, it, vi } from 'vitest';
import { registerAgentCoreIpc } from './agentCoreIpc';

type Handler = (event: { sender: { id: number } }, payload: unknown) => Promise<unknown>;

function setup() {
  const handlers = new Map<string, Handler>();
  const ipcMain = {
    handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)),
  };
  const networkFetch = vi.fn().mockResolvedValue(new Response('{"ok":true}', {
    status: 200,
    statusText: 'OK',
    headers: { 'content-type': 'application/json' },
  }));
  registerAgentCoreIpc(ipcMain, {
    getGeneration: () => ({
      generationId: 'generation-1',
      endpoint: 'http://127.0.0.1:43123',
      bearerToken: 'main-owned-token',
    }),
    isTrustedSender: (event) => event.sender.id === 7,
    fetch: networkFetch,
  });
  return { handlers, ipcMain, networkFetch };
}

describe('Main Agent Core IPC boundary', () => {
  it('rejects untrusted senders before network access', async () => {
    const { handlers, networkFetch } = setup();
    const request = handlers.get('bolt:agent-core:request')!;

    await expect(request({ sender: { id: 99 } }, {
      requestId: '018f47ce-9d6e-4a4b-8c1d-2f3a4b5c6d7e',
      path: '/memory',
      method: 'GET',
    })).rejects.toMatchObject({ code: 'CORE_REQUEST_INVALID' });
    expect(networkFetch).not.toHaveBeenCalled();
  });

  it('filters response headers and rejects oversized bodies', async () => {
    const handlers = new Map<string, Handler>();
    const ipcMain = { handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)) };
    registerAgentCoreIpc(ipcMain, {
      getGeneration: () => ({ generationId: 'generation-1', endpoint: 'http://127.0.0.1:43123', bearerToken: 'token' }),
      isTrustedSender: (event) => event.sender.id === 7,
      fetch: vi.fn().mockResolvedValue(new Response('x'.repeat(17 * 1024 * 1024), {
        headers: { 'content-type': 'text/plain', 'set-cookie': 'secret=1', server: 'internal' },
      })),
    });

    await expect(handlers.get('bolt:agent-core:request')!({ sender: { id: 7 } }, {
      requestId: '018f47ce-9d6e-4a4b-8c1d-2f3a4b5c6d7e', path: '/memory', method: 'GET',
    })).rejects.toMatchObject({ code: 'CORE_RESPONSE_TOO_LARGE' });
  });

  it('rejects a completed response when the verified generation changed before resolve', async () => {
    let current = { generationId: 'generation-1', endpoint: 'http://127.0.0.1:43123', bearerToken: 'token-1' };
    let resolveFetch!: (response: Response) => void;
    const handlers = new Map<string, Handler>();
    const ipcMain = {
      handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)),
    };
    const networkFetch = vi.fn(() => new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    }));
    registerAgentCoreIpc(ipcMain, {
      getGeneration: () => current,
      isTrustedSender: () => true,
      fetch: networkFetch,
    });
    const pending = handlers.get('bolt:agent-core:request')!({ sender: { id: 7 } }, {
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      path: '/memory',
      method: 'GET',
    });

    current = { generationId: 'generation-2', endpoint: 'http://127.0.0.1:43124', bearerToken: 'token-2' };
    resolveFetch(new Response('{"stale":true}', { headers: { 'content-type': 'application/json' } }));

    await expect(pending).rejects.toMatchObject({ code: 'CORE_RESTARTED' });
  });

  it('aborts the network request at timeout and returns CORE_TIMEOUT', async () => {
    vi.useFakeTimers();
    try {
      const handlers = new Map<string, Handler>();
      const ipcMain = {
        handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)),
      };
      let signal: AbortSignal | undefined;
      const networkFetch = vi.fn((_url: string, init?: RequestInit) => {
        signal = init?.signal ?? undefined;
        return new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener('abort', () => reject(signal?.reason));
        });
      });
      registerAgentCoreIpc(ipcMain, {
        getGeneration: () => ({ generationId: 'generation-1', endpoint: 'http://127.0.0.1:43123', bearerToken: 'token' }),
        isTrustedSender: () => true,
        fetch: networkFetch,
      });
      const pending = handlers.get('bolt:agent-core:request')!({ sender: { id: 7 } }, {
        requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
        path: '/memory',
        method: 'GET',
        timeoutMs: 1000,
      });
      const rejection = expect(pending).rejects.toMatchObject({ code: 'CORE_TIMEOUT' });

      await vi.advanceTimersByTimeAsync(1000);

      await rejection;
      expect(signal?.aborted).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('rejects SSE before reading or buffering its body', async () => {
    const handlers = new Map<string, Handler>();
    const ipcMain = {
      handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)),
    };
    const text = vi.fn();
    const networkFetch = vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: new Headers({ 'content-type': 'text/event-stream' }),
      text,
    });
    registerAgentCoreIpc(ipcMain, {
      getGeneration: () => ({ generationId: 'generation-1', endpoint: 'http://127.0.0.1:43123', bearerToken: 'token' }),
      isTrustedSender: () => true,
      fetch: networkFetch as unknown as typeof fetch,
    });

    await expect(handlers.get('bolt:agent-core:request')!({ sender: { id: 7 } }, {
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      path: '/memory',
      method: 'GET',
    })).rejects.toMatchObject({ code: 'CORE_STREAMING_UNSUPPORTED' });
    expect(text).not.toHaveBeenCalled();
  });

  it.each([
    [{ requestId: 'id', path: '/memory', method: 'TRACE' }, 'CORE_METHOD_NOT_ALLOWED'],
    [{ requestId: 'id', path: '//example.com/memory', method: 'GET' }, 'CORE_REQUEST_INVALID'],
    [{ requestId: 'id', path: '/memory', method: 'GET', extra: true }, 'CORE_REQUEST_INVALID'],
    [{ requestId: 'id', path: '/memory', method: 'GET', headers: [['Accept', 'application/json']] }, 'CORE_HEADER_NOT_ALLOWED'],
    [{ requestId: 'id', path: '/memory', method: 'GET', headers: [['accept', 'text/event-stream']] }, 'CORE_HEADER_NOT_ALLOWED'],
    [{ requestId: 'id', path: '/memory', method: 'GET', body: '{}' }, 'CORE_REQUEST_INVALID'],
  ])('rejects invalid request schema before network access: %j', async (payload, code) => {
    const { handlers, networkFetch } = setup();
    const request = handlers.get('bolt:agent-core:request')!;

    await expect(request({ sender: { id: 7 } }, payload)).rejects.toMatchObject({ code });
    expect(networkFetch).not.toHaveBeenCalled();
  });

  it.each(['authorization', 'cookie', 'host', 'proxy-authorization'])(
    'rejects protected %s headers before network access',
    async (header) => {
      const { handlers, networkFetch } = setup();
      const request = handlers.get('bolt:agent-core:request')!;

      await expect(request({ sender: { id: 7 } }, {
        requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
        path: '/memory',
        method: 'GET',
        headers: [[header, 'renderer-controlled']],
      })).rejects.toMatchObject({ code: 'CORE_HEADER_NOT_ALLOWED' });

      expect(networkFetch).not.toHaveBeenCalled();
    },
  );

  it('targets only the verified endpoint and adds the Main-owned bearer', async () => {
    const { handlers, networkFetch } = setup();
    const request = handlers.get('bolt:agent-core:request')!;

    const result = await request({ sender: { id: 7 } }, {
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      path: '/memory',
      method: 'GET',
      headers: [['accept', 'application/json']],
    });

    expect(networkFetch).toHaveBeenCalledWith('http://127.0.0.1:43123/memory', expect.objectContaining({
      method: 'GET',
      redirect: 'error',
    }));
    const init = networkFetch.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('authorization')).toBe('Bearer main-owned-token');
    expect(result).toEqual({
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      generationId: 'generation-1',
      status: 200,
      statusText: 'OK',
      headers: [['content-type', 'application/json']],
      body: '{"ok":true}',
    });
  });

  it('returns already_finished when the owner cancels a settled request', async () => {
    const { handlers } = setup();
    const request = handlers.get('bolt:agent-core:request')!;
    const cancel = handlers.get('bolt:agent-core:cancel')!;
    const requestId = '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e';

    await request({ sender: { id: 7 } }, {
      requestId,
      path: '/memory',
      method: 'GET',
    });

    await expect(cancel({ sender: { id: 7 } }, { requestId })).resolves.toBe('already_finished');
    await expect(cancel({ sender: { id: 8 } }, { requestId }))
      .rejects.toMatchObject({ code: 'CORE_REQUEST_INVALID' });
  });

  it('cancels only an active request owned by the same webContents', async () => {
    let observedSignal: AbortSignal | undefined;
    const handlers = new Map<string, Handler>();
    const ipcMain = {
      handle: vi.fn((channel: string, handler: Handler) => handlers.set(channel, handler)),
    };
    const networkFetch = vi.fn((_url: string, init?: RequestInit) => {
      observedSignal = init?.signal ?? undefined;
      return new Promise<Response>((_resolve, reject) => {
        observedSignal?.addEventListener('abort', () => reject(observedSignal?.reason));
      });
    });
    registerAgentCoreIpc(ipcMain, {
      getGeneration: () => ({ generationId: 'generation-1', endpoint: 'http://127.0.0.1:43123', bearerToken: 'token' }),
      isTrustedSender: () => true,
      fetch: networkFetch,
    });
    const request = handlers.get('bolt:agent-core:request')!;
    const cancel = handlers.get('bolt:agent-core:cancel')!;
    const pending = request({ sender: { id: 7 } }, {
      requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
      path: '/memory',
      method: 'GET',
    });

    await expect(cancel({ sender: { id: 8 } }, { requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e' }))
      .rejects.toMatchObject({ code: 'CORE_REQUEST_INVALID' });
    await expect(cancel({ sender: { id: 7 } }, { requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e' }))
      .resolves.toBe('cancelled');
    expect(observedSignal?.aborted).toBe(true);
    await expect(pending).rejects.toMatchObject({ code: 'CORE_CANCELLED' });
  });
});
