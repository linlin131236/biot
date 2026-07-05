import { describe, expect, it, vi } from 'vitest';
import { approvePermission, consolidateMemory, createHarnessRun, fetchHarnessTrace, fetchMemoryRecords, fetchMemorySnapshot, fetchModelSettingsStatus, fetchPendingPermissions, recordMemory, rejectPermission, resolveMemory, runAgentStep, runDocumentGardener, saveModelSettings, submitToolRequest } from './harnessClient';

describe('harness client', () => {
  it('creates a harness run', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'run_1', goal: 'test' })));

    const run = await createHarnessRun('http://core', 'test', fetcher);

    expect(run.id).toBe('run_1');
    expect(fetcher).toHaveBeenCalledWith('http://core/harness/runs', expect.objectContaining({ method: 'POST' }));
  });

  it('submits a read-only tool request', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_1', status: 'executed', reason: 'execution completed', output: 'done' })));

    const result = await submitToolRequest('http://core', 'run_1', { tool: 'file.read', operation: 'read', payload: { path: 'D:/Bolt/Bolt/README.md' } }, fetcher);

    expect(result.status).toBe('executed');
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'file.read', operation: 'read', payload: { path: 'D:/Bolt/Bolt/README.md' } }) })
    );
  });

  it('submits a file write request for diff review', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_2', status: 'pending_permission', reason: '{"diff":"+new"}' })));

    const result = await submitToolRequest('http://core', 'run_1', { tool: 'file.write', operation: 'write', payload: { path: 'D:/Bolt/Bolt/app.ts', proposed_content: 'new' } }, fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'file.write', operation: 'write', payload: { path: 'D:/Bolt/Bolt/app.ts', proposed_content: 'new' } }) })
    );
  });

  it('submits a shell execute request for confirmation', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_3', status: 'pending_permission', reason: 'known command execution' })));

    const result = await submitToolRequest('http://core', 'run_1', { tool: 'shell.execute', operation: 'command', payload: { command: 'pnpm test', workdir: 'D:/Bolt/Bolt' } }, fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith(
      'http://core/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'shell.execute', operation: 'command', payload: { command: 'pnpm test', workdir: 'D:/Bolt/Bolt' } }) })
    );
  });

  it('runs an agent step', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok' } })));

    const result = await runAgentStep('http://core', 'run_1', fetcher);

    expect(result.status).toBe('executed');
    expect(fetcher).toHaveBeenCalledWith('http://core/harness/runs/run_1/agent-steps', { method: 'POST' });
  });

  it('loads and saves model settings', async () => {
    const payload = { provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2, has_api_key: false };
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(payload))));

    const loaded = await fetchModelSettingsStatus('http://core', fetcher);
    const saved = await saveModelSettings('http://core', { provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2 }, fetcher);

    expect(loaded.model).toBe('fake-model');
    expect(saved.has_api_key).toBe(false);
    expect(fetcher).toHaveBeenCalledWith('http://core/model/settings');
  });

  it('records queries resolves and consolidates memory', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.includes('/consolidate')) return Promise.resolve(new Response(JSON.stringify({ created: 1, sources: 2 })));
      if (input.includes('/resolve')) return Promise.resolve(new Response(JSON.stringify({ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'resolved', source: 'test' })));
      if (input.includes('/records')) return Promise.resolve(new Response(JSON.stringify([{ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'active', source: 'test' }])));
      return Promise.resolve(new Response(JSON.stringify({ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'active', source: 'test' })));
    });

    const created = await recordMemory('http://core', { kind: 'session', scope: 'run_1', content: 'I prefer Tauri' }, fetcher);
    const records = await fetchMemoryRecords('http://core', { kind: 'session', query: 'tauri' }, fetcher);
    const resolved = await resolveMemory('http://core', created.id, fetcher);
    const consolidated = await consolidateMemory('http://core', fetcher);

    expect(records[0].content).toContain('Tauri');
    expect(resolved.status).toBe('resolved');
    expect(consolidated.created).toBe(1);
  });

  it('fetches trace events', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify([{ run_id: 'run_1', sequence: 1, type: 'run.created', payload: {} }])));

    const trace = await fetchHarnessTrace('http://core', 'run_1', fetcher);

    expect(trace[0].type).toBe('run.created');
  });

  it('fetches pending permissions', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify([{ request_id: 'tool_1', status: 'pending_permission' }])));

    const pending = await fetchPendingPermissions('http://core', fetcher);

    expect(pending[0].request_id).toBe('tool_1');
    expect(fetcher).toHaveBeenCalledWith('http://core/permissions/pending');
  });

  it('approves and rejects permissions', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ request_id: 'tool_1', status: 'approved', reason: 'ok' }))));

    const approved = await approvePermission('http://core', 'tool_1', fetcher);
    const rejected = await rejectPermission('http://core', 'tool_1', fetcher);

    expect(approved.status).toBe('approved');
    expect(rejected.request_id).toBe('tool_1');
  });

  it('runs document gardener for a run', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_1', status: 'pending_permission', reason: 'workspace write' })));

    const result = await runDocumentGardener('http://core', 'run_1', fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith('http://core/maintenance/document-gardener/runs/run_1', { method: 'POST' });
  });

  it('throws readable errors for failed responses', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('bad gateway', { status: 502, statusText: 'Bad Gateway' }));

    await expect(fetchMemorySnapshot('http://core', fetcher)).rejects.toThrow('Agent Core request failed: 502 Bad Gateway');
  });
});
