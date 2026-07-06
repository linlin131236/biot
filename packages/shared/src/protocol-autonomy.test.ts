import { describe, expect, it } from 'vitest';
import type { Goal, GoalStatus, TimelineEvent, GoalEvidence, ReviewResult, Checkpoint } from './protocol-autonomy';

describe('shared autonomy protocol', () => {
  it('supports Goal shape', () => {
    const goal: Goal = {
      id: 'goal_abc12345',
      objective: '修复 README',
      criteria: ['拼写已修正'],
      status: 'paused',
      max_steps: 10,
      max_cost: 5.0,
      max_wall_time: 300,
      workspace: 'D:/Projects/Bolt',
      step_count: 3,
    };
    expect(goal.status).toBe('paused');
    expect(goal.step_count).toBe(3);
  });

  it('covers all GoalStatus values', () => {
    const statuses: GoalStatus[] = ['pending', 'running', 'paused', 'stopped', 'completed', 'failed', 'rejected'];
    expect(statuses).toHaveLength(7);
  });

  it('supports TimelineEvent shape', () => {
    const event: TimelineEvent = { type: 'run.created', sequence: 1, payload: {} };
    expect(event.type).toBe('run.created');
    expect(event.sequence).toBe(1);
  });

  it('supports GoalEvidence shape', () => {
    const evidence: GoalEvidence = { phase: 'test', action: 'pytest', result: 'pass', summary: '299 ok' };
    expect(evidence.phase).toBe('test');
    expect(evidence.summary).toBe('299 ok');
  });

  it('supports Checkpoint shape', () => {
    const cp: Checkpoint = {
      id: 'cp_1234abcd',
      run_id: 'run_1',
      goal_id: 'goal_1',
      changed_files: ['main.py'],
      constraints: [],
      pending_permissions: [],
      evidence_refs: [],
    };
    expect(cp.changed_files).toHaveLength(1);
  });

  it('supports ReviewResult shape', () => {
    const result: ReviewResult = { passed: false, failures: ['lint'] };
    expect(result.passed).toBe(false);
    expect(result.failures).toContain('lint');
  });
});
