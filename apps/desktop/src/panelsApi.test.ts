import { describe, expect, it, vi } from 'vitest';
import { createPanelsApi } from './panelsApi';

describe('createPanelsApi adapter bindings', () => {
  it('binds sleepWake methods to the injected fetcher', async () => {
    const fetcher = vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    const api = createPanelsApi(fetcher, null);

    await api.sleepWake.fetchStatus();
    await api.sleepWake.sleep({ reason: 'pause' });
    await api.sleepWake.wake({ trigger: 'resume' });

    expect(fetcher.mock.calls.length).toBeGreaterThanOrEqual(3);
  });
});
