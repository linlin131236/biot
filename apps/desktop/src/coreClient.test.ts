import { describe, expect, it, vi } from 'vitest';
import { fetchCoreHealth } from './coreClient';

describe('core client', () => {
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

  it('returns down when health endpoint fails', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('offline'));

    const status = await fetchCoreHealth(fetcher);

    expect(status).toBe('down');
  });
});
