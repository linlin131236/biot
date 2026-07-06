import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CheckpointPanel } from './CheckpointPanel';
import type { Checkpoint } from '@bolt/shared/autonomy';

const sampleCp: Checkpoint = {
  id: 'cp_abc12345', run_id: 'run_1', goal_id: 'goal_1',
  changed_files: ['a.ts', 'b.ts'], constraints: [], pending_permissions: ['perm_1'], evidence_refs: [],
};

describe('CheckpointPanel', () => {
  const mockApi = {
    createCheckpoint: vi.fn<() => Promise<Checkpoint>>(),
    loadCheckpoint: vi.fn<() => Promise<Checkpoint | null>>(),
  };

  it('disables create when no runId/goalId', () => {
    render(<CheckpointPanel runId={null} goalId={null} api={mockApi} />);
    expect(screen.getByRole('button', { name: '创建检查点' })).toBeDisabled();
  });

  it('shows 暂无目标 when no goalId', () => {
    render(<CheckpointPanel runId="run_1" goalId={null} api={mockApi} />);
    expect(screen.getByText('暂无目标，无法创建检查点')).toBeInTheDocument();
  });

  it('creates checkpoint and shows summary', async () => {
    mockApi.createCheckpoint.mockResolvedValue(sampleCp);
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} baseUrl="http://core" />);
    fireEvent.click(screen.getByRole('button', { name: '创建检查点' }));
    await waitFor(() => expect(screen.getByText(/cp_abc12345/)).toBeInTheDocument());
    expect(screen.getByText('2 个变更文件')).toBeInTheDocument();
    expect(screen.getByText('1 个待审批')).toBeInTheDocument();
    expect(mockApi.createCheckpoint).toHaveBeenCalledWith('http://core', { run_id: 'run_1', goal_id: 'goal_1' });
  });

  it('shows error on create failure', async () => {
    mockApi.createCheckpoint.mockRejectedValue(new Error('fail'));
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} />);
    fireEvent.click(screen.getByRole('button', { name: '创建检查点' }));
    await waitFor(() => expect(screen.getByText('检查点创建失败')).toBeInTheDocument());
  });

  it('loads checkpoint and shows summary', async () => {
    mockApi.loadCheckpoint.mockResolvedValue(sampleCp);
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('检查点 ID');
    fireEvent.change(input, { target: { value: 'cp_abc12345' } });
    fireEvent.click(screen.getByRole('button', { name: '加载检查点' }));
    await waitFor(() => expect(screen.getByText(/cp_abc12345/)).toBeInTheDocument());
    expect(mockApi.loadCheckpoint).toHaveBeenCalledWith('http://core', 'cp_abc12345');
  });

  it('does not show 未找到检查点 before clicking load', () => {
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('检查点 ID');
    fireEvent.change(input, { target: { value: 'cp_maybe' } });
    expect(screen.queryByText('未找到检查点')).toBeNull();
  });

  it('shows 未找到检查点 for null result after clicking load', async () => {
    mockApi.loadCheckpoint.mockResolvedValue(null);
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('检查点 ID');
    fireEvent.change(input, { target: { value: 'cp_bad' } });
    fireEvent.click(screen.getByRole('button', { name: '加载检查点' }));
    await waitFor(() => expect(screen.getByText('未找到检查点')).toBeInTheDocument());
  });

  it('shows error on load failure', async () => {
    mockApi.loadCheckpoint.mockRejectedValue(new Error('fail'));
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} />);
    const input = screen.getByLabelText('检查点 ID');
    fireEvent.change(input, { target: { value: 'cp_x' } });
    fireEvent.click(screen.getByRole('button', { name: '加载检查点' }));
    await waitFor(() => expect(screen.getByText('检查点加载失败')).toBeInTheDocument());
  });

  it('has no rollback or write buttons — only create and load', () => {
    render(<CheckpointPanel runId="run_1" goalId="goal_1" api={mockApi} />);
    const buttons = screen.getAllByRole('button');
    const names = buttons.map(b => b.textContent);
    expect(names).toContain('创建检查点');
    expect(names).toContain('加载检查点');
    expect(names).not.toContain('回滚');
    expect(names).not.toContain('恢复');
    expect(names).not.toContain('写入');
    expect(names).not.toContain('删除');
  });
});
