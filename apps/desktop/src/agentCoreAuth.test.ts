import { describe, expect, it, vi } from 'vitest';
import { createAgentCoreFetcher } from './agentCoreAuth';

describe('agent core authenticated fetcher', () => {
  it('delegates local Agent Core requests to the desktop bridge without exposing the token', async () => {
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreFetch: vi.fn().mockResolvedValue({
        status: 200,
        statusText: 'OK',
        headers: [['content-type', 'application/json']],
        body: '{"ok":true}'
      })
    };
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'));

    const response = await createAgentCoreFetcher(fetcher)('http://localhost:8000/memory', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{"query":"x"}'
    });

    expect(fetcher).not.toHaveBeenCalled();
    expect(window.bolt.agentCoreFetch).toHaveBeenCalledWith('http://localhost:8000/memory', {
      method: 'POST',
      headers: [['content-type', 'application/json']],
      body: '{"query":"x"}'
    });
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it('does not send external URLs through the authenticated desktop bridge', async () => {
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreFetch: vi.fn()
    };
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'));

    await createAgentCoreFetcher(fetcher)('https://example.com/memory', {
      headers: { authorization: 'Bearer explicit-token' }
    });

    expect(window.bolt.agentCoreFetch).not.toHaveBeenCalled();
    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('authorization')).toBe('Bearer explicit-token');
  });
});
