import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ExecutionAuditDiagnostic, ExecutionAuditTimelineEvent, ExecutionHandoffRecord } from '@bolt/shared/autonomy';
import ExecutionHandoffPanel, { type ExecutionHandoffPanelApi } from './ExecutionHandoffPanel';

const baseUrl = 'http://core';
const fetcher = vi.fn();

function record(overrides: Partial<ExecutionHandoffRecord> = {}): ExecutionHandoffRecord {
  return {
    id: 'eh_1',
    queue_item_id: 'eq_1',
    closure_id: 'cl_1',
    kind: 'verification_command',
    status: 'ready_for_manual_action',
    handoff_type: 'manual_verification',
    title: '记录验证命令',
    instruction: '请在外部终端人工运行命令，并回来记录结果',
    command: 'pytest',
    goal_objective: '',
    run_id: null,
    goal_id: null,
    permission_request_id: null,
    permission_status: 'not_requested',
    bridge_error: '',
    result: '',
    ...overrides,
  };
}

function timelineEvent(overrides: Partial<ExecutionAuditTimelineEvent> = {}): ExecutionAuditTimelineEvent {
  return {
    id: 'audit_1',
    closure_id: 'cl_1',
    source: 'permission',
    status: 'pending_permission',
    label: '等待权限',
    summary: '权限请求正在等待人工处理',
    occurred_at: 10,
    queue_item_id: 'eq_1',
    handoff_id: 'eh_1',
    permission_request_id: 'tool_1',
    ...overrides,
  };
}

function diagnostic(overrides: Partial<ExecutionAuditDiagnostic> = {}): ExecutionAuditDiagnostic {
  return {
    id: 'diag_1',
    code: 'missing_pending_permission',
    severity: 'blocking',
    severity_label: '阻断',
    closure_id: 'cl_1',
    queue_item_id: 'eq_1',
    handoff_id: 'eh_1',
    permission_request_id: 'tool_1',
    summary: '交接等待权限，但权限队列没有 pending 项',
    suggestion: '建议人工处理',
    ...overrides,
  };
}

function apiFixture(overrides: Partial<ExecutionHandoffPanelApi> = {}): ExecutionHandoffPanelApi {
  return {
    fetchExecutionHandoffs: vi.fn().mockResolvedValue([record()]),
    fetchExecutionAuditTimeline: vi.fn().mockResolvedValue([]),
    fetchExecutionAuditDiagnostics: vi.fn().mockResolvedValue([]),
    createExecutionHandoff: vi.fn().mockResolvedValue(record()),
    completeExecutionHandoff: vi.fn().mockResolvedValue(record({ status: 'completed' })),
    failExecutionHandoff: vi.fn().mockResolvedValue(record({ status: 'failed' })),
    requestExecutionHandoffPermission: vi.fn().mockResolvedValue(record({ status: 'waiting_permission', permission_status: 'pending_permission', permission_request_id: 'tool_1' })),
    ...overrides,
  };
}

describe('ExecutionHandoffPanel', () => {
  it('没有 closureId 显示暂无闭环任务', () => {
    render(<ExecutionHandoffPanel baseUrl={baseUrl} api={apiFixture()} />);

    expect(screen.getByText('安全交接')).toBeInTheDocument();
    expect(screen.getByText('暂无闭环任务')).toBeInTheDocument();
  });

  it('manual_verification 显示人工运行命令且不出现执行命令按钮', async () => {
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" selectedQueueItemId="eq_1" api={apiFixture()} />);

    expect(await screen.findByText('请在外部终端人工运行')).toBeInTheDocument();
    expect(screen.getByText('pytest')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '执行命令' })).not.toBeInTheDocument();
  });

  it('permission_panel 不出现批准权限按钮', async () => {
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([record({ handoff_type: 'permission_panel', status: 'waiting_permission' })]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('请到权限面板处理原始权限请求')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批准权限' })).not.toBeInTheDocument();
  });

  it('goal_input 显示建议目标但不自动创建目标或运行 loop', async () => {
    const runAgentLoop = vi.fn();
    const createGoal = vi.fn();
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([record({ kind: 'repair_suggestion', handoff_type: 'goal_input', status: 'linked_to_goal', goal_objective: '修复失败测试' })]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('建议目标：修复失败测试')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '复制为目标草稿' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '记录为待创建目标' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '复制为目标草稿' }));
    expect(await screen.findByText('已复制为目标草稿')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '记录为待创建目标' }));
    expect(await screen.findByText('已记录为待创建目标')).toBeInTheDocument();
    expect(createGoal).not.toHaveBeenCalled();
    expect(runAgentLoop).not.toHaveBeenCalled();
  });

  it('点击生成安全交接使用注入 fetcher', async () => {
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" selectedQueueItemId="eq_1" fetcher={fetcher} api={api} />);

    fireEvent.click(screen.getByRole('button', { name: '生成安全交接' }));

    await vi.waitFor(() => expect(api.createExecutionHandoff).toHaveBeenCalledWith(baseUrl, 'eq_1', fetcher));
  });

  it('生成交接返回其他闭环时不追加记录', async () => {
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([]), createExecutionHandoff: vi.fn().mockResolvedValue(record({ closure_id: 'cl_old' })) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" selectedQueueItemId="eq_old" api={api} />);

    fireEvent.click(screen.getByRole('button', { name: '生成安全交接' }));

    expect(await screen.findByText('交接记录不属于当前闭环任务')).toBeInTheDocument();
    expect(screen.queryByText('记录验证命令')).not.toBeInTheDocument();
  });

  it('可标记完成和失败', async () => {
    const api = apiFixture();
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '标记完成' }));
    await vi.waitFor(() => expect(api.completeExecutionHandoff).toHaveBeenCalledWith(baseUrl, 'eh_1', '用户已完成', fetcher));
  });

  it('终态不显示操作按钮', async () => {
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([record({ status: 'completed' })]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('记录验证命令')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记完成' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '标记失败' })).not.toBeInTheDocument();
  });

  it('点击申请人工执行权限只调用 request-permission API', async () => {
    const runAgentLoop = vi.fn();
    const approvePermission = vi.fn();
    const shell = vi.fn();
    const api = apiFixture();
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" fetcher={fetcher} api={api} />);

    fireEvent.click(await screen.findByRole('button', { name: '申请人工执行权限' }));

    await vi.waitFor(() => expect(api.requestExecutionHandoffPermission).toHaveBeenCalledWith(baseUrl, 'eh_1', fetcher));
    expect(runAgentLoop).not.toHaveBeenCalled();
    expect(approvePermission).not.toHaveBeenCalled();
    expect(shell).not.toHaveBeenCalled();
  });

  it('等待权限和申请失败显示中文状态', async () => {
    const api = apiFixture({ fetchExecutionHandoffs: vi.fn().mockResolvedValue([
      record({ status: 'waiting_permission', permission_status: 'pending_permission', permission_request_id: 'tool_1' }),
      record({ id: 'eh_2', status: 'failed', permission_status: 'denied', bridge_error: '危险命令被拒绝' }),
    ]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('等待人工执行权限')).toBeInTheDocument();
    expect(await screen.findByText('申请失败：危险命令被拒绝')).toBeInTheDocument();
    expect(screen.queryByText('auto execute')).not.toBeInTheDocument();
  });

  it('不调用 runAgentLoop / approvePermission / shell / fs / process / ipcRenderer', async () => {
    const runAgentLoop = vi.fn();
    const approvePermission = vi.fn();
    const shell = vi.fn();
    const fs = vi.fn();
    const process = vi.fn();
    const ipcRenderer = vi.fn();
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={apiFixture()} />);

    fireEvent.click(await screen.findByRole('button', { name: '标记完成' }));

    expect(runAgentLoop).not.toHaveBeenCalled();
    expect(approvePermission).not.toHaveBeenCalled();
    expect(shell).not.toHaveBeenCalled();
    expect(fs).not.toHaveBeenCalled();
    expect(process).not.toHaveBeenCalled();
    expect(ipcRenderer).not.toHaveBeenCalled();
  });

  it('只读展示执行审计时间线中文状态', async () => {
    const api = apiFixture({
      fetchExecutionAuditTimeline: vi.fn().mockResolvedValue([
        timelineEvent({ id: 'audit_1', status: 'approved', label: '已批准队列', summary: '队列项已由人工批准' }),
        timelineEvent({ id: 'audit_2', status: 'pending_permission', label: '等待权限', summary: '权限请求正在等待人工处理' }),
        timelineEvent({ id: 'audit_3', status: 'executed', label: '已执行', summary: '权限执行已返回结果' }),
      ]),
    });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('执行审计时间线')).toBeInTheDocument();
    expect(screen.getByText('已批准队列')).toBeInTheDocument();
    expect(screen.getByText('等待权限')).toBeInTheDocument();
    expect(screen.getByText('已执行')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批准权限' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '执行命令' })).not.toBeInTheDocument();
  });

  it('只读展示审计一致性诊断，不提供自动修复能力', async () => {
    const api = apiFixture({ fetchExecutionAuditDiagnostics: vi.fn().mockResolvedValue([diagnostic()]) });
    render(<ExecutionHandoffPanel baseUrl={baseUrl} closureId="cl_1" api={api} />);

    expect(await screen.findByText('审计一致性诊断')).toBeInTheDocument();
    expect(screen.getByText('阻断')).toBeInTheDocument();
    expect(screen.getByText('交接等待权限，但权限队列没有 pending 项')).toBeInTheDocument();
    expect(screen.getByText('建议人工处理')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '自动修复' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批准权限' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '执行命令' })).not.toBeInTheDocument();
  });
});
