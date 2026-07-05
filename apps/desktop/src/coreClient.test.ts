import { describe, expect, it, vi } from 'vitest';
import { fetchCoreHealth } from './coreClient';

describe('core client', () => {
  it('returns ok when health endpoint responds', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', service: 'bolt-agent-core' }))
    );

    const status = await fetchCoreHealth('http://127.0.0.1:9876', fetcher);

    expect(status).toBe('ok');
    expect(fetcher).toHaveBeenCalledWith('http://127.0.0.1:9876/health');
  });

  it('returns down when health endpoint fails', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('offline'));

    const status = await fetchCoreHealth('http://127.0.0.1:9876', fetcher);

    expect(status).toBe('down');
  });
});
