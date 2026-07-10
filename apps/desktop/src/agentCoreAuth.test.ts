import { describe, expect, it, vi } from 'vitest';
import { createAgentCoreTransport, type AgentCoreIpcResponse } from './agentCoreAuth';

describe('agent core IPC transport adapter', () => {
  it('returns a request handle synchronously before the response settles', () => {
    let resolveDto!: (value: AgentCoreIpcResponse) => void;
    const dto = new Promise<AgentCoreIpcResponse>((resolve) => {
      resolveDto = resolve;
    });
    const cancel = vi.fn().mockResolvedValue('cancelled' as const);
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreRequest: vi.fn().mockReturnValue({
        requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
        response: dto,
        cancel,
      }),
    };

    const handle = createAgentCoreTransport()('/memory', { method: 'GET' });

    expect(handle.requestId).toBe('018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e');
    expect(handle.response).toBeInstanceOf(Promise);
    expect(window.bolt.agentCoreRequest).toHaveBeenCalledWith('/memory', { method: 'GET' });
    resolveDto({
      requestId: handle.requestId,
      generationId: 'generation-1',
      status: 200,
      statusText: 'OK',
      headers: [['content-type', 'application/json']],
      body: '{"ok":true}',
    });
  });

  it('rebuilds the copyable response DTO as a Response inside Renderer', async () => {
    const requestId = '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e';
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreRequest: vi.fn().mockReturnValue({
        requestId,
        response: Promise.resolve({
          requestId,
          generationId: 'generation-1',
          status: 201,
          statusText: 'Created',
          headers: [['content-type', 'application/json']],
          body: '{"ok":true}',
        }),
        cancel: vi.fn().mockResolvedValue('already_finished'),
      }),
    };

    const handle = createAgentCoreTransport()('/memory', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{"query":"x"}',
    });
    const response = await handle.response;

    expect(response).toBeInstanceOf(Response);
    expect(response.status).toBe(201);
    expect(response.statusText).toBe('Created');
    expect(response.headers.get('content-type')).toBe('application/json');
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it('delegates cancellation to the bridge handle', async () => {
    const cancel = vi.fn().mockResolvedValue('cancelled' as const);
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreRequest: vi.fn().mockReturnValue({
        requestId: '018f47ce-9d6e-7a4b-8c1d-2f3a4b5c6d7e',
        response: new Promise<AgentCoreIpcResponse>(() => undefined),
        cancel,
      }),
    };

    const handle = createAgentCoreTransport()('/memory');

    await expect(handle.cancel()).resolves.toBe('cancelled');
    expect(cancel).toHaveBeenCalledOnce();
  });

  it('fails closed when the desktop bridge is unavailable', () => {
    window.bolt = { selectWorkspace: vi.fn() };

    expect(() => createAgentCoreTransport()('/memory')).toThrow('bridge');
  });

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
});
