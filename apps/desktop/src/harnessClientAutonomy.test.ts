import { describe, expect, it, vi } from 'vitest';
import { createCheckpoint, evaluateReview, fetchSkills, loadCheckpoint } from './harnessClientAutonomy';

describe('harness autonomy client', () => {
  it('calls checkpoint endpoints', async () => {
    const checkpoint = {
      id: 'cp_1234abcd',
      run_id: 'run_1',
      goal_id: 'goal_1',
      changed_files: ['main.txt'],
      file_contents: { 'main.txt': 'hello' },
      constraints: [],
      pending_permissions: [],
      evidence_refs: [],
    };
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/checkpoints/cp_1234abcd')) {
        return Promise.resolve(new Response(JSON.stringify(checkpoint)));
      }
      return Promise.resolve(new Response(JSON.stringify(checkpoint)));
    });

    const created = await createCheckpoint('http://core', { run_id: 'run_1', goal_id: 'goal_1' }, fetcher);
    const loaded = await loadCheckpoint('http://core', 'cp_1234abcd', fetcher);

    expect(created.id).toBe('cp_1234abcd');
    expect(loaded?.file_contents?.['main.txt']).toBe('hello');
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/checkpoints',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ run_id: 'run_1', goal_id: 'goal_1' }) }),
    );
    expect(fetcher).toHaveBeenCalledWith('http://core/checkpoints/cp_1234abcd');
  });

  it('calls review gate endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ passed: false, failures: ['desktop build'] })));

    const result = await evaluateReview('http://core', {
      items: ['pytest', 'desktop build'],
      results: { pytest: true, 'desktop build': false },
    }, fetcher);

    expect(result.failures).toEqual(['desktop build']);
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/review/evaluate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ items: ['pytest', 'desktop build'], results: { pytest: true, 'desktop build': false } }),
      }),
    );
  });

  it('keeps skills explicitly unwired until the backend has a route', async () => {
    const fetcher = vi.fn();

    await expect(fetchSkills('http://core', fetcher)).rejects.toThrow('/skills endpoint not registered');
    expect(fetcher).not.toHaveBeenCalled();
  });
});
