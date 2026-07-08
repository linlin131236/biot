import { describe, expect, it, vi } from 'vitest';
import { createAgentCoreFetcher } from './agentCoreAuth';

describe('agent core authenticated fetcher', () => {
  it('adds bearer token from the desktop bridge', async () => {
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreAuth: vi.fn().mockResolvedValue('local-token')
    };
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'));

    await createAgentCoreFetcher(fetcher)('http://core/memory');

    expect(fetcher).toHaveBeenCalledWith('http://core/memory', {
      headers: expect.any(Headers)
    });
    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('authorization')).toBe('Bearer local-token');
  });

  it('keeps explicit authorization headers unchanged', async () => {
    window.bolt = {
      selectWorkspace: vi.fn(),
      agentCoreAuth: vi.fn().mockResolvedValue('local-token')
    };
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'));

    await createAgentCoreFetcher(fetcher)('http://core/memory', {
      headers: { authorization: 'Bearer explicit-token' }
    });

    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('authorization')).toBe('Bearer explicit-token');
  });
});
