import { describe, expect, it } from 'vitest';
import { isHarnessRun, isMemorySnapshot, isToolRequest, type AgentStepResult, type ChangeSet, type ContextPacket, type MemoryConsolidationResult, type MemoryQuery, type MemorySnapshot, type ModelSettingsStatus, type PendingPermission, type ShellCommandPayload, type ToolRequest, type TraceEvent, type ToolResult } from './protocol';

describe('shared protocol', () => {
  it('recognizes harness run payloads', () => {
    expect(isHarnessRun({ id: 'run_1', goal: 'test' })).toBe(true);
    expect(isHarnessRun({ id: 'run_1' })).toBe(false);
  });

  it('supports tool result and trace event shapes', () => {
    const result: ToolResult = { request_id: 'tool_1', status: 'denied', reason: 'blocked' };
    const event: TraceEvent = { run_id: 'run_1', sequence: 1, type: 'tool.requested', payload: {} };

    expect(result.status).toBe('denied');
    expect(event.sequence).toBe(1);
  });

  it('recognizes memory snapshot payloads', () => {
    const snapshot: MemorySnapshot = {
      records: [{ id: 'mem_1', kind: 'project', scope: 'repo', content: 'Uses pnpm', status: 'active', source: 'test' }],
      p0_context: { unresolved_failures: [], hard_constraints: [] }
    };

    expect(isMemorySnapshot(snapshot)).toBe(true);
    expect(isMemorySnapshot({ records: [] })).toBe(false);
  });

  it('recognizes tool request payloads', () => {
    const request: ToolRequest = { tool: 'file.read', operation: 'read', payload: { path: 'D:/Bolt/Bolt/README.md' } };

    expect(isToolRequest(request)).toBe(true);
    expect(isToolRequest({ tool: 'file.read', operation: 'read' })).toBe(false);
  });

  it('supports shell execute request payloads', () => {
    const payload: ShellCommandPayload = { command: 'pnpm test', workdir: 'D:/Bolt/Bolt', timeout_seconds: 60 };
    const request: ToolRequest = { tool: 'shell.execute', operation: 'command', payload: { ...payload } };

    expect(isToolRequest(request)).toBe(true);
    expect(request.payload.command).toBe('pnpm test');
  });

  it('supports model settings and agent step payloads', () => {
    const settings: ModelSettingsStatus = { provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2, has_api_key: false };
    const result: AgentStepResult = { status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok' } };

    expect(settings.has_api_key).toBe(false);
    expect(result.tool_result?.status).toBe('executed');
  });

  it('supports context packet payloads', () => {
    const packet: ContextPacket = { goal: 'read', p0_context: { unresolved_failures: [], hard_constraints: [] }, recent_trace: [], token_budget: 8000, memory_context: [] };

    expect(packet.token_budget).toBe(8000);
  });

  it('supports write change set payloads', () => {
    const change: ChangeSet = {
      path: 'D:/Bolt/Bolt/src/app.ts',
      base_hash: 'abc',
      proposed: 'new',
      diff: '--- a\n+++ b',
      status: 'pending_review'
    };
    const permission: PendingPermission = {
      id: 'perm_tool_1',
      run_id: 'run_1',
      request_id: 'tool_1',
      tool: 'file.write',
      operation: 'write',
      payload: { path: change.path, change_set: change },
      action: 'confirm_with_diff',
      reason: JSON.stringify(change),
      status: 'pending_permission'
    };

    expect(permission.payload.change_set).toEqual(change);
  });

  it('supports layered memory query and consolidation payloads', () => {
    const snapshot: MemorySnapshot = {
      records: [{ id: 'mem_1', kind: 'long_term', scope: 'global', content: 'Use local memory', status: 'active', source: 'test', metadata: { confidence: 1 }, created_at: 'now', updated_at: 'now' }],
      p0_context: { unresolved_failures: [], hard_constraints: [] }
    };
    const query: MemoryQuery = { kind: 'long_term', status: 'active', query: 'local' };
    const result: MemoryConsolidationResult = { created: 1, sources: 2 };

    expect(isMemorySnapshot(snapshot)).toBe(true);
    expect(query.kind).toBe('long_term');
    expect(result.created).toBe(1);
  });

  it('supports pending permission and approved result shapes', () => {
    const permission: PendingPermission = {
      id: 'perm_tool_1',
      run_id: 'run_1',
      request_id: 'tool_1',
      tool: 'shell.run',
      operation: 'command',
      payload: { command: 'pnpm test' },
      action: 'confirm',
      reason: 'safe command execution',
      status: 'pending_permission'
    };
    const result: ToolResult = { request_id: 'tool_1', status: 'approved', reason: 'approved without execution' };
    const executed: ToolResult = { request_id: 'tool_1', status: 'executed', reason: 'execution completed', output: 'done', error: null };

    expect(permission.status).toBe('pending_permission');
    expect(result.status).toBe('approved');
    expect(executed.output).toBe('done');
  });
});
