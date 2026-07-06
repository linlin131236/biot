import { describe, expect, it, vi } from 'vitest';
import { createCheckpoint, evaluateReview, fetchSkills, loadCheckpoint, clearGoal, fetchGoalEvidence, fetchGoalBudget, fetchUnfinishedGoals, fetchRunTimeline } from './harnessClientAutonomy';
import { runAgentLoop } from './harnessClient';
import type { AgentLoopResult } from '@bolt/shared';

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

  it('calls clearGoal endpoint', async () => {
    const stopped = { id: 'goal_1', status: 'stopped' };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(stopped)));
    const result = await clearGoal('http://core', 'goal_1', fetcher);
    expect(result.status).toBe('stopped');
    expect(fetcher).toHaveBeenCalledWith('http://core/goals/goal_1/clear', expect.objectContaining({ method: 'POST' }));
  });

  it('calls fetchGoalEvidence endpoint', async () => {
    const evidence = [{ phase: 'test', result: 'pass' }];
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(evidence)));
    const result = await fetchGoalEvidence('http://core', 'goal_1', fetcher);
    expect(result).toHaveLength(1);
    expect(fetcher).toHaveBeenCalledWith('http://core/goals/goal_1/evidence');
  });

  it('calls fetchGoalBudget endpoint', async () => {
    const budget = { spent: 0.5, limit: 5.0 };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(budget)));
    const result = await fetchGoalBudget('http://core', 'goal_1', fetcher);
    expect(result.spent).toBe(0.5);
    expect(fetcher).toHaveBeenCalledWith('http://core/goals/goal_1/budget');
  });

  it('calls runAgentLoop endpoint with typed result', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 3 };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(loopResult)));
    const result = await runAgentLoop('http://core', 'run_1', 10, fetcher);
    expect(result.status).toBe('executed');
    expect(result.steps).toBe(3);
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/harness/runs/run_1/agent-loops',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ max_steps: 10 }) }),
    );
  });

  it('calls fetchUnfinishedGoals endpoint', async () => {
    const goals = [{ id: 'goal_1', objective: 'test', status: 'paused' }];
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(goals)));
    const result = await fetchUnfinishedGoals('http://core', fetcher);
    expect(result).toHaveLength(1);
    expect(fetcher).toHaveBeenCalledWith('http://core/goals/unfinished');
  });

  it('calls fetchRunTimeline endpoint', async () => {
    const timeline = [{ type: 'run.created', sequence: 1 }];
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(timeline)));
    const result = await fetchRunTimeline('http://core', 'run_1', fetcher);
    expect(result).toHaveLength(1);
    expect(fetcher).toHaveBeenCalledWith('http://core/runs/run_1/timeline');
  });
});
