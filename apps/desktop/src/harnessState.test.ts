import { describe, expect, it } from 'vitest';
import { createBoltState, reduceBoltState } from './state';

describe('Bolt harness state', () => {
  it('stores current harness run id', () => {
    const state = reduceBoltState(createBoltState(), { type: 'harness.run.created', runId: 'run_1' });

    expect(state.currentRunId).toBe('run_1');
  });

  it('stores trace events', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'harness.trace.loaded',
      events: [{ run_id: 'run_1', sequence: 1, type: 'run.created', payload: {} }]
    });

    expect(state.traceEvents[0].type).toBe('run.created');
  });

  it('stores memory snapshot', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'memory.snapshot.loaded',
      snapshot: { records: [], p0_context: { unresolved_failures: [], hard_constraints: [] } }
    });

    expect(state.memorySnapshot?.records).toHaveLength(0);
  });

  it('stores pending permissions', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'permissions.pending.loaded',
      permissions: [{
        id: 'perm_tool_1',
        run_id: 'run_1',
        request_id: 'tool_1',
        tool: 'shell.run',
        operation: 'command',
        payload: { command: 'pnpm test' },
        action: 'confirm',
        reason: 'safe command execution',
        status: 'pending_permission'
      }]
    });

    expect(state.pendingPermissions[0].request_id).toBe('tool_1');
  });

  it('stores tool execution results', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'tool.result.recorded',
      result: { request_id: 'tool_1', status: 'executed', reason: 'execution completed', output: 'done' }
    });

    expect(state.toolResults[0].status).toBe('executed');
  });
});
