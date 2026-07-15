import { describe, expect, it, vi } from 'vitest';
import { fetchRuntimeStatuses } from './runtimeClient';

describe('runtime client', () => {
  it('uses the existing relative Core fetcher for Runtime state', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      runtimes: [{
        runtime_id: 'hermes', implementation_version: null, protocol_type: 'acp',
        protocol_version: 'v1', capabilities: {}, state: 'release_unavailable',
        start_available: false, blocked_reason: 'release_unavailable', active_session_count: 0,
      }],
    })));

    const runtimes = await fetchRuntimeStatuses(fetcher);

    expect(fetcher).toHaveBeenCalledWith('/runtime');
    expect(runtimes[0].runtime_id).toBe('hermes');
    expect(runtimes[0].state).toBe('release_unavailable');
  });

  it('propagates a non-success Core response without inspecting its body', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('provider-secret', {
      status: 502, statusText: 'Bad Gateway',
    }));

    await expect(fetchRuntimeStatuses(fetcher)).rejects.toThrow('502 Bad Gateway');
  });
});
