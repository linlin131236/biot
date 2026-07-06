/**
 * M32 Desktop Dogfood Smoke — red tests for the real product path.
 *
 * Covers the complete dogfood flow:
 *   1. Create a harness run with workspace
 *   2. Create a goal
 *   3. Create a conversation and add a user message
 *   4. file.read (executed immediately)
 *   5. file.patch → pending_permission
 *   6. Approve permission → verify file changed
 *   7. Create and load a checkpoint
 *   8. Evaluate a review gate
 *   9. Fetch run timeline
 *
 * These tests use mock fetchers (same pattern as harnessClient.test.ts)
 * but exercise the full client chain from UI action to API call.
 */
import { describe, expect, it, vi } from 'vitest';
import {
  createHarnessRun,
  submitToolRequest,
  approvePermission,
  fetchHarnessTrace,
  fetchPendingPermissions,
} from './harnessClient';
import {
  createGoal,
  createConversation,
  addMessage,
  createCheckpoint,
  loadCheckpoint,
  evaluateReview,
  fetchRunTimeline,
  fetchSkills,
} from './harnessClientAutonomy';

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
}

describe('desktop dogfood smoke — full product path', () => {
  it('covers run → goal → conversation → file.read → file.patch → approve → checkpoint → review → timeline', async () => {
    const runId = 'run_dog1';
    const goalId = 'goal_a1b2c3d4';
    const convId = 'conv_smoke';
    const cpId = 'cp_e5f6a7b8';
    const requestId = 'tool_patch1';

    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      // 1. Create run
      if (input === 'http://core/harness/runs' && init?.method === 'POST') {
        return Promise.resolve(json({ id: runId, goal: 'dogfood smoke', workspace: 'C:/Workspace' }));
      }
      // 2. Create goal
      if (input === 'http://core/goals' && init?.method === 'POST') {
        return Promise.resolve(json({
          id: goalId,
          objective: 'run dogfood smoke',
          criteria: ['file read', 'patch approved', 'checkpoint loaded'],
          status: 'pending',
          workspace: 'C:/Workspace',
          max_steps: 10,
          max_cost: 5.0,
          max_wall_time: 300,
          steps_taken: 0,
          cost_spent: 0,
          evidence: [],
        }));
      }
      // 3. Create conversation
      if (input === 'http://core/conversations' && init?.method === 'POST') {
        return Promise.resolve(json({ id: convId }));
      }
      // 4. Add message
      if (input === `http://core/conversations/${convId}/messages` && init?.method === 'POST') {
        return Promise.resolve(json({ status: 'ok' }));
      }
      // 5. file.read — executed immediately
      if (input === `http://core/harness/runs/${runId}/tool-requests` && init?.method === 'POST') {
        const body = JSON.parse((init as RequestInit & { body: string }).body as string);
        if (body.tool === 'file.read') {
          return Promise.resolve(json({
            request_id: 'tool_read1',
            status: 'executed',
            reason: 'execution completed',
            output: 'hello bolt',
          }));
        }
        // 6. file.patch → pending_permission
        if (body.tool === 'file.patch') {
          return Promise.resolve(json({
            request_id: requestId,
            status: 'pending_permission',
            reason: 'workspace write requires approval',
          }));
        }
      }
      // 7. Approve permission
      if (input === `http://core/permissions/${requestId}/approve`) {
        return Promise.resolve(json({
          request_id: requestId,
          status: 'executed',
          reason: 'permission approved',
          output: 'patch applied',
        }));
      }
      // 8. Create checkpoint
      if (input === 'http://core/checkpoints' && init?.method === 'POST') {
        return Promise.resolve(json({
          id: cpId,
          run_id: runId,
          goal_id: goalId,
          changed_files: ['main.txt'],
          file_contents: { 'main.txt': 'hello bolt' },
          constraints: ['do not add new agent capability'],
          pending_permissions: [],
          evidence_refs: [requestId],
        }));
      }
      // 9. Load checkpoint
      if (input === `http://core/checkpoints/${cpId}`) {
        return Promise.resolve(json({
          id: cpId,
          run_id: runId,
          goal_id: goalId,
          changed_files: ['main.txt'],
          file_contents: { 'main.txt': 'hello bolt' },
          constraints: ['do not add new agent capability'],
          pending_permissions: [],
          evidence_refs: [requestId],
        }));
      }
      // 10. Review evaluate
      if (input === 'http://core/review/evaluate' && init?.method === 'POST') {
        return Promise.resolve(json({ passed: false, failures: ['desktop build'] }));
      }
      // 11. Timeline
      if (input === `http://core/runs/${runId}/timeline`) {
        return Promise.resolve(json([
          { run_id: runId, sequence: 1, type: 'run.created', payload: {} },
          { run_id: runId, sequence: 2, type: 'agent.loop.started', payload: {} },
        ]));
      }
      // Trace fallback
      if (input === `http://core/harness/runs/${runId}/trace`) {
        return Promise.resolve(json([
          { run_id: runId, sequence: 1, type: 'run.created', payload: {} },
        ]));
      }
      // Pending permissions fallback
      if (input === 'http://core/permissions/pending') {
        return Promise.resolve(json([]));
      }
      return Promise.resolve(json({}));
    });

    // Step 1: Create run
    const run = await createHarnessRun('http://core', 'dogfood smoke', 'C:/Workspace', fetcher);
    expect(run.id).toBe(runId);
    expect(run.workspace).toBe('C:/Workspace');

    // Step 2: Create goal
    const goal = await createGoal('http://core', {
      objective: 'run dogfood smoke',
      criteria: ['file read', 'patch approved', 'checkpoint loaded'],
      max_steps: 10,
      max_cost: 5.0,
      max_wall_time: 300,
      workspace: 'C:/Workspace',
    }, fetcher);
    expect(goal.id).toBe(goalId);
    expect(goal.status).toBe('pending');

    // Step 3: Create conversation + add message
    const conv = await createConversation('http://core', { system_prompt: 'stay scoped' }, fetcher);
    expect(conv.id).toBe(convId);
    const msgResult = await addMessage('http://core', convId, { role: 'user', content: 'run smoke' }, fetcher);
    expect(msgResult.status).toBe('ok');

    // Step 4: file.read — executed immediately
    const readResult = await submitToolRequest('http://core', runId, {
      tool: 'file.read', operation: 'read', payload: { path: 'C:/Workspace/main.txt' },
    }, fetcher);
    expect(readResult.status).toBe('executed');
    expect(readResult.output).toBe('hello bolt');

    // Step 5: file.patch → pending_permission
    const patchResult = await submitToolRequest('http://core', runId, {
      tool: 'file.patch', operation: 'patch',
      payload: { path: 'C:/Workspace/main.txt', old_string: 'hello', new_string: 'hello bolt' },
    }, fetcher);
    expect(patchResult.status).toBe('pending_permission');
    expect(patchResult.request_id).toBe(requestId);

    // Step 6: Approve permission
    const approved = await approvePermission('http://core', requestId, fetcher);
    expect(approved.status).toBe('executed');

    // Step 7: Create and load checkpoint
    const checkpoint = await createCheckpoint('http://core', {
      run_id: runId, goal_id: goalId,
      changed_files: ['main.txt'],
      constraints: ['do not add new agent capability'],
      pending_permissions: [],
      evidence_refs: [requestId],
    }, fetcher);
    expect(checkpoint.id).toBe(cpId);
    expect(checkpoint.file_contents?.['main.txt']).toBe('hello bolt');
    expect(checkpoint.constraints).toEqual(['do not add new agent capability']);

    const loaded = await loadCheckpoint('http://core', cpId, fetcher);
    expect(loaded?.file_contents?.['main.txt']).toBe('hello bolt');
    expect(loaded?.constraints).toEqual(['do not add new agent capability']);

    // Step 8: Review evaluate — intentional failure
    const review = await evaluateReview('http://core', {
      items: ['pytest', 'desktop build'],
      results: { pytest: true, 'desktop build': false },
    }, fetcher);
    expect(review.passed).toBe(false);
    expect(review.failures).toEqual(['desktop build']);

    // Step 9: Fetch timeline
    const timeline = await fetchRunTimeline('http://core', runId, fetcher);
    expect(timeline.length).toBeGreaterThanOrEqual(2);
    expect((timeline as { type: string }[]).some((e) => e.type === 'agent.loop.started')).toBe(true);
  });

  it('unwired surfaces throw explicitly instead of returning fake data', async () => {
    const fetcher = vi.fn();
    await expect(fetchSkills('http://core', fetcher)).rejects.toThrow('/skills endpoint not registered');
    expect(fetcher).not.toHaveBeenCalled();
  });
});
