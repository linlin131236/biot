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

    fireEvent.change(screen.getByLabelText('工作区路径'), { target: { value: 'D:/Bolt/Bolt' } });
    fireEvent.click(screen.getByRole('button', { name: '进入工作台' }));

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByText('D:/Bolt/Bolt')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).toContain('D:/Bolt/Bolt');
  });

  it('restores the last run from local storage', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core', lastRunId: 'run_7' }));

    render(<App />);

    expect(screen.getByText('Last run')).toBeInTheDocument();
    expect(screen.getByText('run_7')).toBeInTheDocument();
  });

  it('shows a readable error when a core action fails', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('network down'));
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.click(screen.getByRole('button', { name: '刷新 Memory' }));

    expect(await screen.findByText(/无法连接 Agent Core/)).toBeInTheDocument();
  });

  it('renders perception memory and pending diff permissions', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core' }));

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
});
