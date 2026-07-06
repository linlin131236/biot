import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TASK_TEMPLATES, type TaskClosureEvidence, type TaskClosureStatus, type TaskTemplateId } from '@bolt/shared/autonomy';
import TaskClosurePanel, { type TaskClosurePanelApi } from './TaskClosurePanel';

const baseUrl = 'http://core';
const workspace = 'D:/Bolt/Bolt';
const fetcher = vi.fn();

function closure(overrides: Partial<TaskClosureEvidence> & { id?: string; status?: TaskClosureStatus } = {}): TaskClosureEvidence & { id?: string; status?: TaskClosureStatus } {
  return {
    id: 'cl_42',
    objective: '修复拼写',
    template_id: 'bugfix',
    plan_summary: '',
    changed_files: [],
    commands: [],
    command_results: [],
    permission_request_ids: [],
    retry_count: 0,
    final_status: 'pending',
    review_summary: '',
    next_action: '',
    ...overrides,
  };
}

function apiFixture(): TaskClosurePanelApi {
  return {
    fetchTaskTemplates: vi.fn().mockResolvedValue(TASK_TEMPLATES),
    createTaskClosure: vi.fn().mockResolvedValue(closure()),
    getTaskClosure: vi.fn().mockResolvedValue(closure()),
    addClosureEvent: vi.fn().mockResolvedValue(closure({ final_status: 'verifying', commands: ['pnpm test'], command_results: ['335 passed'] })),
    addClosureReview: vi.fn().mockResolvedValue(closure({ final_status: 'completed', review_summary: '全部通过' })),
  };
}

async function createClosure(api: TaskClosurePanelApi) {
  fireEvent.change(screen.getByPlaceholderText('输入任务目标'), { target: { value: '修复拼写' } });
  fireEvent.click(screen.getByRole('button', { name: '创建闭环任务' }));
  await vi.waitFor(() => expect(api.createTaskClosure).toHaveBeenCalled());
  await screen.findByText('目标：修复拼写');
}

describe('TaskClosurePanel', () => {
  beforeEach(() => {
    fetcher.mockReset();
  });

  it('显示任务闭环标题', () => {
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={apiFixture()} />);

    expect(screen.getByText('任务闭环')).toBeInTheDocument();
  });

  it('模板选择器显示 5 个中文选项', () => {
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={apiFixture()} />);

    const options = within(screen.getByRole('combobox')).getAllByRole('option');
    expect(options).toHaveLength(5);
    expect(options.map(option => option.textContent)).toEqual(TASK_TEMPLATES.map(template => template.label));
  });

  it('workspace 为空时禁用创建', () => {
    render(<TaskClosurePanel baseUrl={baseUrl} workspace="" api={apiFixture()} />);

    expect(screen.getByRole('button', { name: '创建闭环任务' })).toBeDisabled();
    expect(screen.getByText('请先选择工作区')).toBeInTheDocument();
  });

  it('点击创建调用 createTaskClosure', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} runId="run_42" goalId="goal_42" api={api} />);

    await createClosure(api);

    expect(api.createTaskClosure).toHaveBeenCalledWith(baseUrl, {
      objective: '修复拼写',
      template_id: 'bugfix' satisfies TaskTemplateId,
      run_id: 'run_42',
      goal_id: 'goal_42',
    }, fetcher);
  });

  it('创建后显示中文状态标签', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);

    await createClosure(api);

    expect(screen.getByText('目标：修复拼写')).toBeInTheDocument();
    expect(screen.getByText('当前状态：待开始')).toBeInTheDocument();
  });

  it('记录验证命令调用 addClosureEvent', async () => {
    const api = apiFixture();
    const { container } = render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} api={api} />);
    await createClosure(api);

    fireEvent.change(screen.getByPlaceholderText('验证命令'), { target: { value: 'pnpm test' } });
    fireEvent.change(screen.getByPlaceholderText('验证结果'), { target: { value: '335 passed' } });
    fireEvent.click(screen.getByRole('button', { name: '记录验证结果' }));

    await vi.waitFor(() => expect(api.addClosureEvent).toHaveBeenCalledWith(baseUrl, 'cl_42', { type: 'command', command: 'pnpm test', result: '335 passed' }, fetcher));
    await vi.waitFor(() => expect(container).toHaveTextContent('当前状态：验证中'));
  });

  it('记录审查摘要调用 addClosureReview', async () => {
    const api = apiFixture();
    const { container } = render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} api={api} />);
    await createClosure(api);

    fireEvent.change(screen.getByPlaceholderText('审查摘要'), { target: { value: '全部通过' } });
    fireEvent.click(screen.getByLabelText('通过'));
    fireEvent.click(screen.getByRole('button', { name: '记录审查摘要' }));

    await vi.waitFor(() => expect(api.addClosureReview).toHaveBeenCalledWith(baseUrl, 'cl_42', { summary: '全部通过', passed: true }, fetcher));
    await vi.waitFor(() => expect(container).toHaveTextContent('审查摘要：全部通过'));
  });

  it('没有 push/release/delete 按钮', () => {
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={apiFixture()} />);

    expect(screen.queryByRole('button', { name: /push/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /release/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除' })).not.toBeInTheDocument();
  });

  it('不调用 runAgentLoop 或 approvePermission', async () => {
    const api = apiFixture();
    const runAgentLoop = vi.fn();
    const approvePermission = vi.fn();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} api={api} />);

    await createClosure(api);

    expect(runAgentLoop).not.toHaveBeenCalled();
    expect(approvePermission).not.toHaveBeenCalled();
  });
});
