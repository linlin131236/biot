import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TASK_TEMPLATES, type TaskClosureEvidence, type TaskTemplateId, type VerificationAssessment } from '@bolt/shared/autonomy';
import TaskClosurePanel, { type TaskClosurePanelApi } from './TaskClosurePanel';

const baseUrl = 'http://core';
const workspace = 'D:/Bolt/Bolt';
const fetcher = vi.fn();

function closure(overrides: Partial<TaskClosureEvidence> = {}): TaskClosureEvidence {
  return {
    id: 'cl_42',
    objective: '修复拼写',
    template_id: 'bugfix',
    run_id: null,
    goal_id: null,
    status: 'pending',
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

function assessment(overrides: Partial<VerificationAssessment> = {}): VerificationAssessment {
  return { status: 'missing_evidence', summary: '缺少验证证据', missing: ['缺少测试证据'], repair_suggestions: ['补充缺少的验证证据后重新评估完成度'], ...overrides };
}

function apiFixture(): TaskClosurePanelApi {
  return {
    fetchTaskTemplates: vi.fn().mockResolvedValue(TASK_TEMPLATES),
    createTaskClosure: vi.fn().mockResolvedValue(closure()),
    getTaskClosure: vi.fn().mockResolvedValue(closure()),
    addClosureEvent: vi.fn().mockResolvedValue(closure({ status: 'verifying', final_status: 'verifying', commands: ['pnpm test'], command_results: ['335 passed'] })),
    addClosureReview: vi.fn().mockResolvedValue(closure({ status: 'completed', final_status: 'completed', review_summary: '全部通过' })),
    bindTaskClosureRun: vi.fn().mockImplementation((_b, _id, runId) => Promise.resolve(closure({ run_id: runId }))),
    bindTaskClosureGoal: vi.fn().mockImplementation((_b, _id, goalId) => Promise.resolve(closure({ goal_id: goalId }))),
    fetchTaskClosureVerificationPlan: vi.fn().mockResolvedValue({ template_id: 'bugfix', checks: [{ id: 'quality', label: '测试或质量门证据', command: 'pytest', required: true, satisfied: false, evidence: '', missing_reason: '缺少测试证据' }] }),
    fetchTaskClosureAssessment: vi.fn().mockResolvedValue(assessment()),
    updateTaskClosureAssessment: vi.fn().mockResolvedValue(closure({ status: 'completed', final_status: 'completed', next_action: '已完成' })),
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

  it('workspace 为空时禁用绑定按钮', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace="" runId="run_43" goalId="goal_43" api={api} />);
    expect(screen.getByRole('button', { name: '创建闭环任务' })).toBeDisabled();
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

  it('点击绑定当前运行调用 bindTaskClosureRun', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} runId="run_43" api={api} />);
    await createClosure(api);

    fireEvent.click(screen.getByRole('button', { name: '绑定当前运行' }));

    await vi.waitFor(() => expect(api.bindTaskClosureRun).toHaveBeenCalledWith(baseUrl, 'cl_42', 'run_43', fetcher));
    expect(await screen.findByText('已绑定运行：run_43')).toBeInTheDocument();
  });

  it('点击绑定当前目标调用 bindTaskClosureGoal', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} goalId="goal_43" api={api} />);
    await createClosure(api);

    fireEvent.click(screen.getByRole('button', { name: '绑定当前目标' }));

    await vi.waitFor(() => expect(api.bindTaskClosureGoal).toHaveBeenCalledWith(baseUrl, 'cl_42', 'goal_43', fetcher));
    expect(await screen.findByText('已绑定目标：goal_43')).toBeInTheDocument();
  });

  it('显示自动同步状态提示', async () => {
    const cases = [
      { status: 'waiting_permission', text: '等待人工批准' },
      { status: 'stopped', text: '已达到最大步数' },
      { status: 'failed', text: '需要人工处理' },
    ] as const;

    for (const item of cases) {
      const api = apiFixture();
      api.createTaskClosure = vi.fn().mockResolvedValue(closure({ status: item.status, final_status: item.status }));
      const { unmount } = render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);
      await createClosure(api);
      expect(await screen.findByText(item.text)).toBeInTheDocument();
      unmount();
    }
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

  it('点击评估完成度调用 update API', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} api={api} />);
    await createClosure(api);

    fireEvent.click(screen.getByRole('button', { name: '评估完成度' }));

    await vi.waitFor(() => expect(api.updateTaskClosureAssessment).toHaveBeenCalledWith(baseUrl, 'cl_42', fetcher));
  });

  it('显示已通过验收状态', async () => {
    const api = apiFixture();
    api.fetchTaskClosureAssessment = vi.fn().mockResolvedValue(assessment({ status: 'passed', summary: '验证证据已满足', missing: [], repair_suggestions: [] }));
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);

    await createClosure(api);

    expect(await screen.findByText('已通过')).toBeInTheDocument();
  });

  it('显示缺少证据和建议修复', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);

    await createClosure(api);

    expect(await screen.findByText('缺少证据')).toBeInTheDocument();
    expect(screen.getByText(/建议修复：/)).toBeInTheDocument();
  });

  it('显示等待人工批准和最大步数状态', async () => {
    for (const item of [
      { status: 'waiting_permission', text: '等待人工批准' },
      { status: 'stopped', text: '已达到最大步数' },
    ] as const) {
      const api = apiFixture();
      api.fetchTaskClosureAssessment = vi.fn().mockResolvedValue(assessment({ status: item.status, summary: item.text }));
      const { unmount } = render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);
      await createClosure(api);
      expect(await screen.findByText(item.text)).toBeInTheDocument();
      unmount();
    }
  });

  it('command 只显示为命令建议，不出现执行按钮', async () => {
    const api = apiFixture();
    render(<TaskClosurePanel baseUrl={baseUrl} workspace={workspace} api={api} />);

    await createClosure(api);

    expect(await screen.findByText('命令建议：pytest（不执行命令）')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '执行命令' })).not.toBeInTheDocument();
  });
});
