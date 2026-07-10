import { describe, expect, it, vi } from 'vitest';
import { approvePermission, consolidateMemory, createHarnessRun, deleteDesktopApiKey, fetchDesktopSettings, fetchHarnessTrace, fetchMemoryRecords, fetchMemorySnapshot, fetchModelSettingsStatus, fetchPendingPermissions, recordMemory, rejectPermission, resolveMemory, runAgentLoop, runAgentStep, runDocumentGardener, saveDesktopApiKey, saveModelSettings, submitToolRequest } from './harnessClient';

describe('harness client', () => {
  it('creates a harness run', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'run_1', goal: 'test', workspace: 'D:/Projects/App' })));

    const run = await createHarnessRun('test', 'D:/Projects/App', fetcher);

    expect(run.id).toBe('run_1');
    expect(run.workspace).toBe('D:/Projects/App');
    expect(fetcher).toHaveBeenCalledWith('/harness/runs', expect.objectContaining({ method: 'POST', body: JSON.stringify({ goal: 'test', workspace: 'D:/Projects/App' }) }));
  });

  it('submits a read-only tool request', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_1', status: 'executed', reason: 'execution completed', output: 'done' })));

    const result = await submitToolRequest('run_1', { tool: 'file.read', operation: 'read', payload: { path: 'C:/Projects/Bolt/README.md' } }, fetcher);

    expect(result.status).toBe('executed');
    expect(fetcher).toHaveBeenCalledWith(
      '/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'file.read', operation: 'read', payload: { path: 'C:/Projects/Bolt/README.md' } }) })
    );
  });

  it('submits a file write request for diff review', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_2', status: 'pending_permission', reason: '{"diff":"+new"}' })));

    const result = await submitToolRequest('run_1', { tool: 'file.write', operation: 'write', payload: { path: 'C:/Projects/Bolt/app.ts', proposed_content: 'new' } }, fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith(
      '/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'file.write', operation: 'write', payload: { path: 'C:/Projects/Bolt/app.ts', proposed_content: 'new' } }) })
    );
  });

  it('submits a shell execute request for confirmation', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_3', status: 'pending_permission', reason: 'known command execution' })));

    const result = await submitToolRequest('run_1', { tool: 'shell.execute', operation: 'command', payload: { command: 'pnpm test', workdir: 'C:/Projects/Bolt' } }, fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith(
      '/harness/runs/run_1/tool-requests',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ tool: 'shell.execute', operation: 'command', payload: { command: 'pnpm test', workdir: 'C:/Projects/Bolt' } }) })
    );
  });

  it('runs an agent step', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok' } })));

    const result = await runAgentStep('run_1', fetcher);

    expect(result.status).toBe('executed');
    expect(fetcher).toHaveBeenCalledWith('/harness/runs/run_1/agent-steps', { method: 'POST' });
  });

  it('loads and saves model settings', async () => {
    const payload = { provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2, has_api_key: false };
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(payload))));

    const loaded = await fetchModelSettingsStatus(fetcher);
    const saved = await saveModelSettings({ provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2 }, fetcher);

    expect(loaded.model).toBe('fake-model');
    expect(saved.has_api_key).toBe(false);
    expect(fetcher).toHaveBeenCalledWith('/model/settings');
  });

  it('uses the dedicated revision-bound credential endpoints', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => Promise.resolve(new Response(JSON.stringify(
      input.includes('/desktop/settings/api-key')
        ? { status: 'ok', has_api_key: true, revision: 8 }
        : { theme: 'light', language: 'zh-CN', default_workspace: '', has_api_key: true, credential_revision: 7 },
    ))));

    const settings = await fetchDesktopSettings(fetcher);
    const saved = await saveDesktopApiKey('synthetic-secret', settings.credential_revision, fetcher);
    await deleteDesktopApiKey(saved.revision, fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      '/desktop/settings/api-key',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ api_key: 'synthetic-secret', revision: 7 }) }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      '/desktop/settings/api-key?revision=8',
      { method: 'DELETE' },
    );
  });

  it('records queries resolves and consolidates memory', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.includes('/consolidate')) return Promise.resolve(new Response(JSON.stringify({ created: 1, sources: 2 })));
      if (input.includes('/resolve')) return Promise.resolve(new Response(JSON.stringify({ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'resolved', source: 'test' })));
      if (input.includes('/records')) return Promise.resolve(new Response(JSON.stringify([{ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'active', source: 'test' }])));
      return Promise.resolve(new Response(JSON.stringify({ id: 'mem_1', kind: 'session', scope: 'run_1', content: 'I prefer Tauri', status: 'active', source: 'test' })));
    });

    const created = await recordMemory({ kind: 'session', scope: 'run_1', content: 'I prefer Tauri' }, fetcher);
    const records = await fetchMemoryRecords({ kind: 'session', query: 'tauri' }, fetcher);
    const resolved = await resolveMemory(created.id, fetcher);
    const consolidated = await consolidateMemory(fetcher);

    expect(records[0].content).toContain('Tauri');
    expect(resolved.status).toBe('resolved');
    expect(consolidated.created).toBe(1);
  });

  it('fetches trace events', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify([{ run_id: 'run_1', sequence: 1, type: 'run.created', payload: {} }])));

    const trace = await fetchHarnessTrace('run_1', fetcher);

    expect(trace[0].type).toBe('run.created');
  });

  it('fetches pending permissions', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify([{ request_id: 'tool_1', status: 'pending_permission' }])));

    const pending = await fetchPendingPermissions(fetcher);

    expect(pending[0].request_id).toBe('tool_1');
    expect(fetcher).toHaveBeenCalledWith('/permissions/pending');
  });

  it('approves and rejects permissions', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ request_id: 'tool_1', status: 'approved', reason: 'ok' }))));

    const approved = await approvePermission('tool_1', fetcher);
    const rejected = await rejectPermission('tool_1', fetcher);

    expect(approved.status).toBe('approved');
    expect(rejected.request_id).toBe('tool_1');
  });

  it('runs an agent loop with bounded max steps', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'executed', steps: 2, last_step: { status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok' } } })));

    const result = await runAgentLoop('run_1', 2, fetcher);

    expect(result.steps).toBe(2);
    expect(fetcher).toHaveBeenCalledWith('/harness/runs/run_1/agent-loops', expect.objectContaining({ method: 'POST', body: JSON.stringify({ max_steps: 2 }) }));
  });

  it('runs document gardener for a run', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ request_id: 'tool_1', status: 'pending_permission', reason: 'workspace write' })));

    const result = await runDocumentGardener('run_1', fetcher);

    expect(result.status).toBe('pending_permission');
    expect(fetcher).toHaveBeenCalledWith('/maintenance/document-gardener/runs/run_1', { method: 'POST' });
  });

  it('throws readable errors for failed responses', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('bad gateway', { status: 502, statusText: 'Bad Gateway' }));

    await expect(fetchMemorySnapshot(fetcher)).rejects.toThrow('Agent Core request failed: 502 Bad Gateway');
  });
});
