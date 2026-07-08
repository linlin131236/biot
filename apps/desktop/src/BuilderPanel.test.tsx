/**
 * BuilderPanel tests (M160).
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BuilderPanel } from './BuilderPanel';

function fakeApi(executionResult: Record<string, unknown> = {
  task_id: 't1',
  output: { code_changes: 'diff', tests: 'pytest', evidence_refs: [], source_refs: [] },
  proposals: [],
}) {
  return {
    executeTask: vi.fn().mockResolvedValue(executionResult),
    fetchProposals: vi.fn().mockResolvedValue({ proposals: [] }),
  };
}

describe('BuilderPanel', () => {
  it('renders title', () => {
    render(<BuilderPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('构建引擎')).toBeTruthy();
    expect(screen.getByText('产生代码变更提案，需人工审批后应用。')).toBeTruthy();
  });

  it('executes task and shows results', async () => {
    const api = fakeApi({
      task_id: 't1',
      output: { code_changes: 'diff', tests: 'pytest', evidence_refs: [], source_refs: [] },
      proposals: [],
    });
    render(<BuilderPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务 ID'), { target: { value: 't1' } });
    fireEvent.change(screen.getByPlaceholderText('输入构建任务描述'), { target: { value: 'desc' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: '/ws' } });
    fireEvent.click(screen.getByText('执行构建'));
    await waitFor(() => expect(screen.getByText('构建结果')).toBeTruthy());
    expect(screen.getByText('diff')).toBeTruthy();
    expect(screen.getByText('pytest')).toBeTruthy();
  });

  it('shows error state', async () => {
    const api = fakeApi();
    api.executeTask.mockRejectedValueOnce(new Error('网络错误'));
    render(<BuilderPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务 ID'), { target: { value: 't1' } });
    fireEvent.change(screen.getByPlaceholderText('输入构建任务描述'), { target: { value: 'desc' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: '/ws' } });
    fireEvent.click(screen.getByText('执行构建'));
    await waitFor(() => expect(screen.getByText(/执行构建失败/)).toBeTruthy());
  });

  it('shows proposal status', async () => {
    const api = fakeApi({
      task_id: 't1',
      output: { code_changes: 'diff', tests: 'pytest', evidence_refs: [], source_refs: [] },
      proposals: ['p1: pending'],
    });
    render(<BuilderPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务 ID'), { target: { value: 't1' } });
    fireEvent.change(screen.getByPlaceholderText('输入构建任务描述'), { target: { value: 'desc' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: '/ws' } });
    fireEvent.click(screen.getByText('执行构建'));
    await waitFor(() => expect(screen.getByText('提案状态')).toBeTruthy());
    expect(screen.getByText('p1: pending')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<BuilderPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('执行构建')).toBeTruthy();
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });
});
