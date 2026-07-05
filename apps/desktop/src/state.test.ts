import { describe, expect, it } from 'vitest';
import { createBoltState, reduceBoltState } from './state';

describe('Bolt desktop state', () => {
  it('stores selected workspace path', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'workspace.selected',
      path: 'C:/Projects/Bolt'
    });

    expect(state.workspacePath).toBe('C:/Projects/Bolt');
  });

  it('updates agent core health', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'core.health.changed',
      status: 'ok'
    });

    expect(state.coreStatus).toBe('ok');
  });

  it('appends chat messages in order', () => {
    const first = reduceBoltState(createBoltState(), {
      type: 'chat.message.added',
      role: 'user',
      content: 'Build Bolt'
    });
    const second = reduceBoltState(first, {
      type: 'chat.message.added',
      role: 'assistant',
      content: 'Planning next step'
    });

    expect(second.messages).toHaveLength(2);
    expect(second.messages[1].content).toBe('Planning next step');
  });

  it('stores pending diff permissions', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'permissions.pending.loaded',
      permissions: [
        {
          id: 'perm_tool_1',
          run_id: 'run_1',
          request_id: 'tool_1',
          tool: 'file.write',
          operation: 'write',
          payload: { change_set: { path: 'app.ts', base_hash: 'abc', proposed: 'new', diff: '+new', status: 'pending_review' } },
          action: 'confirm_with_diff',
          reason: 'workspace write',
          status: 'pending_permission'
        }
      ]
    });

    expect(state.pendingPermissions[0].action).toBe('confirm_with_diff');
    expect(state.pendingPermissions[0].payload.change_set).toBeTruthy();
  });

  it('stores pending shell permissions', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'permissions.pending.loaded',
      permissions: [
        {
          id: 'perm_tool_2',
          run_id: 'run_1',
          request_id: 'tool_2',
          tool: 'shell.execute',
          operation: 'command',
          payload: { command: 'pnpm test', workdir: 'C:/Projects/Bolt' },
          action: 'confirm',
          reason: 'known command execution',
          status: 'pending_permission'
        }
      ]
    });

    expect(state.pendingPermissions[0].tool).toBe('shell.execute');
    expect(state.pendingPermissions[0].payload.command).toBe('pnpm test');
  });

  it('stores model settings status and agent step results', () => {
    const withSettings = reduceBoltState(createBoltState(), {
      type: 'model.settings.loaded',
      status: { provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2, has_api_key: false }
    });
    const withStep = reduceBoltState(withSettings, {
      type: 'agent.step.recorded',
      result: { status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok' } }
    });

    expect(withStep.modelSettingsStatus?.model).toBe('fake-model');
    expect(withStep.agentStepResults[0].status).toBe('executed');
  });

  it('stores layered memory snapshots and consolidation results', () => {
    const withMemory = reduceBoltState(createBoltState(), {
      type: 'memory.snapshot.loaded',
      snapshot: {
        records: [{ id: 'mem_1', kind: 'long_term', scope: 'global', content: 'Use local memory', status: 'active', source: 'test', metadata: { confidence: 1 } }],
        p0_context: { unresolved_failures: [], hard_constraints: [] }
      }
    });
    const consolidated = reduceBoltState(withMemory, {
      type: 'memory.consolidation.recorded',
      result: { created: 1, sources: 2 }
    });

    expect(consolidated.memorySnapshot?.records[0].kind).toBe('long_term');
    expect(consolidated.memoryConsolidationResult?.created).toBe(1);
  });

  it('records tool results', () => {
    const state = reduceBoltState(createBoltState(), {
      type: 'tool.result.recorded',
      result: { request_id: 'tool_1', status: 'executed', reason: 'execution completed', output: 'change applied' }
    });

    expect(state.toolResults[0].output).toBe('change applied');
  });
});
