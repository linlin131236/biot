import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { App } from './App';

const memorySnapshot = {
  records: [
    {
      id: 'mem_profile',
      kind: 'project' as const,
      scope: 'workspace_profile',
      content: 'Workspace profile captured',
      status: 'active' as const,
      source: 'perception',
      tags: ['perception', 'workspace_profile'],
      metadata: { package_manager: 'pnpm', languages: ['typescript'], truncated: false }
    },
    {
      id: 'mem_snapshot',
      kind: 'session' as const,
      scope: 'run_1',
      content: 'Perception snapshot captured',
      status: 'active' as const,
      source: 'perception',
      tags: ['perception', 'snapshot'],
      metadata: { intent: { category: 'code_change' }, scheduler: [{ priority: 'P1', task: 'workspace_profile', status: 'executed' }] }
    }
  ],
  p0_context: { unresolved_failures: [], hard_constraints: [] }
};

beforeEach(() => {
  localStorage.clear();
});

describe('App', () => {
  it('renders the first-run wizard on a fresh profile', () => {
    render(<App />);

    expect(screen.getByText('首次运行')).toBeInTheDocument();
    expect(screen.getByLabelText('工作区路径')).toBeInTheDocument();
    expect(screen.getByLabelText('Agent Core URL')).toHaveValue('http://localhost:8000');
  });

  it('completes first-run and restores workspace state', () => {
    render(<App />);

    fireEvent.change(screen.getByLabelText('工作区路径'), { target: { value: 'C:/Projects/Bolt' } });
    fireEvent.click(screen.getByRole('button', { name: '进入工作台' }));

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByText('C:/Projects/Bolt')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).toContain('C:/Projects/Bolt');
  });

  it('restores the last run from local storage', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core', lastRunId: 'run_7' }));

    render(<App />);

    expect(screen.getByText('Last run')).toBeInTheDocument();
    expect(screen.getByText('run_7')).toBeInTheDocument();
  });

  it('checks agent core health when the workbench opens', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ status: 'ok', service: 'bolt-agent-core' }));
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);

    expect(await screen.findByText('ok')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('http://core/health');
  });

  it('shows a readable error when a core action fails', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('network down'));
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.click(screen.getByRole('button', { name: '鍒锋柊 Memory' }));

    expect(await screen.findByText(/无法连接 Agent Core/)).toBeInTheDocument();
  });

  it('renders perception memory and pending diff permissions', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App initialMemorySnapshot={memorySnapshot} initialPendingPermissions={[{
      id: 'perm_1',
      run_id: 'run_1',
      request_id: 'tool_1',
      tool: 'file.write',
      operation: 'write',
      payload: { change_set: { path: 'src/App.tsx', base_hash: 'abc', proposed: 'new', diff: '+new', status: 'pending_review' } },
      action: 'confirm_with_diff',
      reason: 'workspace write',
      status: 'pending_permission'
    }]} />);

    expect(screen.getByText('pnpm')).toBeInTheDocument();
    expect(screen.getByText('typescript')).toBeInTheDocument();
    expect(screen.getByText('code_change')).toBeInTheDocument();
    expect(screen.getByText(/src\/App\.tsx/)).toBeInTheDocument();
    expect(screen.getByText(/\+new/)).toBeInTheDocument();
  });

  it('starts a run and executes an agent step from the workbench', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/harness/runs')) return Promise.resolve(json({ id: 'run_9', goal: 'fix bug', workspace: 'C:/Projects/Bolt' }));
      if (input.endsWith('/agent-steps')) return Promise.resolve(json({ status: 'executed', model_output: '{}', tool_result: { request_id: 'tool_1', status: 'executed', reason: 'ok', output: 'done' } }));
      if (input.endsWith('/trace')) return Promise.resolve(json([{ run_id: 'run_9', sequence: 1, type: 'run.created', payload: {} }]));
      if (input.endsWith('/permissions/pending')) return Promise.resolve(json([]));
      if (input.endsWith('/memory')) return Promise.resolve(json({ records: [], p0_context: { unresolved_failures: [], hard_constraints: [] } }));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.change(screen.getByLabelText('浠诲姟鐩爣'), { target: { value: 'fix bug' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start Run' }));
    expect(await screen.findByText('run_9')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('http://core/harness/runs', expect.objectContaining({ body: JSON.stringify({ goal: 'fix bug', workspace: 'C:/Projects/Bolt' }) }));

    fireEvent.click(screen.getByRole('button', { name: 'Run Step' }));
    expect(await screen.findByText('done')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).toContain('run_9');
  });

  it('refreshes trace and approves permissions', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/trace')) return Promise.resolve(json([{ run_id: 'run_1', sequence: 2, type: 'tool.requested', payload: {} }]));
      if (input.endsWith('/approve')) return Promise.resolve(json({ request_id: 'tool_1', status: 'executed', reason: 'ok', output: 'applied' }));
      if (input.endsWith('/permissions/pending')) return Promise.resolve(json([]));
      return Promise.resolve(json({ records: [], p0_context: { unresolved_failures: [], hard_constraints: [] } }));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core', lastRunId: 'run_1' }));

    render(<App fetcher={fetcher} initialPendingPermissions={[{
      id: 'perm_1', run_id: 'run_1', request_id: 'tool_1', tool: 'shell.execute', operation: 'command', payload: { command: 'pnpm test', workdir: 'C:/Projects/Bolt' }, action: 'confirm', reason: 'known command execution', status: 'pending_permission'
    }]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh Trace' }));
    expect(await screen.findByText('tool.requested')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    expect(await screen.findByText('applied')).toBeInTheDocument();
  });

  it('saves model settings without storing api keys locally', async () => {
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (init?.method === 'POST') return Promise.resolve(json({ provider: 'openai-compatible', base_url: 'http://llm', model: 'gpt-test', temperature: 0.2, has_api_key: true }));
      return Promise.resolve(json({ provider: 'fake', base_url: 'http://localhost', model: 'fake-model', temperature: 0.2, has_api_key: false }));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-test' } });
    fireEvent.change(screen.getByLabelText('API Key'), { target: { value: 'secret-key' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save Model Settings' }));

    expect(await screen.findByText('API key configured')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).not.toContain('secret-key');
  });

  it('runs document gardener for the current run', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      return Promise.resolve(json({ request_id: 'tool_9', status: 'pending_permission', reason: 'workspace write' }));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core', lastRunId: 'run_1' }));

    render(<App fetcher={fetcher} />);
    fireEvent.click(screen.getByRole('button', { name: 'Run Document Gardener' }));

    expect(await screen.findByText('workspace write')).toBeInTheDocument();
  });
});

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
}
