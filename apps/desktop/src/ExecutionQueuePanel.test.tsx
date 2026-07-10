import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ExecutionQueueItem } from '@bolt/shared/autonomy';
import ExecutionQueuePanel, { type ExecutionQueuePanelApi } from './ExecutionQueuePanel';
const fetcher = vi.fn();

function item(overrides: Partial<ExecutionQueueItem> = {}): ExecutionQueueItem {
  return {
    id: 'eq_1',
    closure_id: 'cl_1',
    kind: 'verification_command',
    title: '记录验证命令',
    description: '缺少测试证据',
    risk: 'verification_command',
    status: 'pending',
    command: 'pytest',
    reason: '',
    result: '',
    ...overrides,
  };
}

function apiFixture(overrides: Partial<ExecutionQueuePanelApi> = {}): ExecutionQueuePanelApi {
  return {
    fetchExecutionQueue: vi.fn().mockResolvedValue([item()]),
    proposeExecutionQueue: vi.fn().mockResolvedValue([item()]),
    approveExecutionQueueItem: vi.fn().mockResolvedValue(item({ status: 'approved' })),
    rejectExecutionQueueItem: vi.fn().mockResolvedValue(item({ status: 'rejected' })),
    completeExecutionQueueItem: vi.fn().mockResolvedValue(item({ status: 'completed' })),
    failExecutionQueueItem: vi.fn().mockResolvedValue(item({ status: 'failed' })),
    ...overrides,
  };
}

describe('ExecutionQueuePanel', () => {
  it('无 closureId 显示暂无闭环任务', () => {
    render(<ExecutionQueuePanel api={apiFixture()} />);

    expect(screen.getByText('安全执行队列')).toBeInTheDocument();
    expect(screen.getByText('暂无闭环任务')).toBeInTheDocument();
  });

  it('propose 后显示队列项', async () => {
    const api = apiFixture();
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(screen.getByRole('button', { name: '生成待处理动作' }));

    await vi.waitFor(() => expect(api.proposeExecutionQueue).toHaveBeenCalledWith('cl_1', fetcher));
    expect(await screen.findByText('记录验证命令')).toBeInTheDocument();
    expect(screen.getByText('风险等级：验证命令')).toBeInTheDocument();
  });

  it('verification_command 显示命令建议且不出现执行按钮', async () => {
    render(<ExecutionQueuePanel closureId="cl_1" api={apiFixture()} />);

    expect(await screen.findByText('命令建议：pytest（不执行命令）')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '执行命令' })).not.toBeInTheDocument();
  });

  it('approve 调用 approve API', async () => {
    const api = apiFixture();
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    await vi.waitFor(() => expect(api.approveExecutionQueueItem).toHaveBeenCalledWith('eq_1', fetcher));
    expect(await screen.findByText('已批准')).toBeInTheDocument();
  });

  it('approve 后只选择交接队列项，不自动生成 handoff', async () => {
    const api = apiFixture();
    const onApprovedItemChange = vi.fn();
    const createExecutionHandoff = vi.fn();
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} onApprovedItemChange={onApprovedItemChange} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    await vi.waitFor(() => expect(onApprovedItemChange).toHaveBeenCalledWith('eq_1'));
    expect(createExecutionHandoff).not.toHaveBeenCalled();
  });

  it('reject 调用 reject API', async () => {
    const api = apiFixture();
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '拒绝' }));

    await vi.waitFor(() => expect(api.rejectExecutionQueueItem).toHaveBeenCalledWith('eq_1', '用户拒绝', fetcher));
  });

  it('complete 调用 complete API', async () => {
    const api = apiFixture({ fetchExecutionQueue: vi.fn().mockResolvedValue([item({ status: 'approved' })]) });
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '标记完成' }));

    await vi.waitFor(() => expect(api.completeExecutionQueueItem).toHaveBeenCalledWith('eq_1', '用户已完成', fetcher));
  });

  it('fail 调用 fail API', async () => {
    const api = apiFixture({ fetchExecutionQueue: vi.fn().mockResolvedValue([item({ status: 'approved' })]) });
    render(<ExecutionQueuePanel closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '标记失败' }));

    await vi.waitFor(() => expect(api.failExecutionQueueItem).toHaveBeenCalledWith('eq_1', '用户标记失败', fetcher));
  });

  it('verification_command pending 只显示批准和拒绝', async () => {
    render(<ExecutionQueuePanel closureId="cl_1" api={apiFixture()} />);

    expect(await screen.findByRole('button', { name: '批准' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '拒绝' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记完成' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记失败' })).not.toBeInTheDocument();
  });

  it('read_only pending 可直接标记完成', async () => {
    const api = apiFixture({ fetchExecutionQueue: vi.fn().mockResolvedValue([item({ kind: 'manual_review', risk: 'read_only' })]) });
    render(<ExecutionQueuePanel closureId="cl_1" api={api} />);

    expect(await screen.findByRole('button', { name: '标记完成' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记失败' })).not.toBeInTheDocument();
  });

  it('approved 显示完成和失败操作', async () => {
    const api = apiFixture({ fetchExecutionQueue: vi.fn().mockResolvedValue([item({ status: 'approved' })]) });
    render(<ExecutionQueuePanel closureId="cl_1" api={api} />);

    expect(await screen.findByRole('button', { name: '标记完成' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '标记失败' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批准' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '拒绝' })).not.toBeInTheDocument();
  });

  it('终态不显示操作按钮', async () => {
    const api = apiFixture({ fetchExecutionQueue: vi.fn().mockResolvedValue([item({ status: 'completed' })]) });
    render(<ExecutionQueuePanel closureId="cl_1" api={api} />);

    expect(await screen.findByText('已完成')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批准' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '拒绝' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记完成' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记失败' })).not.toBeInTheDocument();
  });

  it('不调用 runAgentLoop / approvePermission / shell', async () => {
    const runAgentLoop = vi.fn();
    const approvePermission = vi.fn();
    const shell = vi.fn();
    render(<ExecutionQueuePanel closureId="cl_1" api={apiFixture()} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    expect(runAgentLoop).not.toHaveBeenCalled();
    expect(approvePermission).not.toHaveBeenCalled();
    expect(shell).not.toHaveBeenCalled();
  });
});
