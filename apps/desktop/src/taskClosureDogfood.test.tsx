import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';

async function settleNetwork(fetcher: { mock: { calls: unknown[] } }) {
  // Root-cause stability: wait until mount-time panel fan-out stops, instead of raising global timeouts.
  let previous = -1;
  await waitFor(() => {
    const current = fetcher.mock.calls.length;
    if (current === previous) return true;
    previous = current;
    throw new Error('panel network still settling');
  }, { timeout: 2000, interval: 50 });
}

function emptyPanelPayload(input: string): unknown {
  if (input.includes('/health')) return { status: 'ok', service: 'bolt-agent-core' };
  if (input.includes('/goals/unfinished')) return [];
  if (input.includes('/execution-audit/integrity')) return [];
  if (input.includes('/planner/graphs')) return [];
  if (input.includes('/release-readiness')) return { ready: true, checks: [], blockers: [], warnings: [] };
  if (input.includes('/local-release-checklist')) return { ready: true, items: [], blockers: [], warnings: [], next_step: '可以发布', disclaimer: '只读' };
  if (input.includes('/recovery-policy')) return { scenarios: [], categories: {}, total: 0, disclaimer: '' };
  if (input.includes('/diagnostics-center')) return { diagnostics: [], integrity: [], total_blockers: 0, total_warnings: 0, total_infos: 0 };
  if (input.includes('/execution-queue')) return [];
  if (input.includes('/execution-handoffs')) return [];
  if (input.includes('/multi-task-queue')) return [];
  if (input.includes('/permissions')) return [];
  if (input.includes('/memory')) return { entries: [] };
  if (input.includes('/skills')) return [];
  if (input.includes('/desktop/settings') || input.includes('/settings/desktop')) return { theme: 'dark', language: 'zh-CN', default_workspace: '', has_api_key: false };
  return {};
}

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
}

describe('M43 task closure dogfood', () => {
  it('creates closure, binds current run, and refreshes automatic status in Chinese', async () => {
    const requests: Array<{ url: string; body: unknown }> = [];
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/goals/unfinished')) return Promise.resolve(json([]));
      if (input.endsWith('/harness/runs') && init?.method === 'POST') return Promise.resolve(json({ id: 'run_43', workspace: 'D:/Bolt/Bolt' }));
      if (input.endsWith('/task-closures') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        requests.push({ url: input, body });
        return Promise.resolve(json(closure({ run_id: body.run_id ?? null, goal_id: body.goal_id ?? null })));
      }
      if (input.endsWith('/task-closures/cl_43/bind-run') && init?.method === 'POST') {
        requests.push({ url: input, body: JSON.parse(String(init.body)) });
        return Promise.resolve(json(closure({ run_id: 'run_43', status: 'executing', final_status: 'executing' })));
      }
      if (input.endsWith('/task-closures/cl_43/verification-plan')) return Promise.resolve(json({ template_id: 'bugfix', checks: [{ id: 'quality', label: '测试或质量门证据', command: 'pytest', required: true, satisfied: false, evidence: '', missing_reason: '缺少测试证据' }] }));
      if (input.endsWith('/task-closures/cl_43/assessment') && init?.method === 'POST') return Promise.resolve(json(closure({ run_id: 'run_43', status: 'waiting_permission', final_status: 'waiting_permission', next_action: '等待人工批准' })));
      if (input.endsWith('/task-closures/cl_43/assessment')) return Promise.resolve(json({ status: 'waiting_permission', summary: '等待人工批准', missing: [], repair_suggestions: ['等待人工批准后再继续验证'] }));
      if (input.endsWith('/task-closures/cl_43')) return Promise.resolve(json(closure({ run_id: 'run_43', status: 'waiting_permission', final_status: 'waiting_permission', permission_request_ids: ['tool_43'] })));
      if (input.endsWith('/execution-audit/integrity')) return Promise.resolve(json([]));
      if (input.endsWith('/release-readiness')) return Promise.resolve(json({ ready: true, checks: [], blockers: [], warnings: [] }));
      if (input.endsWith('/local-release-checklist')) return Promise.resolve(json({ ready: true, items: [], blockers: [], warnings: [], next_step: '可以发布', disclaimer: '只读' }));
      if (input.endsWith('/recovery-policy')) return Promise.resolve(json({ scenarios: [], categories: {}, total: 0, disclaimer: '' }));
      if (input.endsWith('/planner/graphs')) return Promise.resolve(json([]));
      return Promise.resolve(json(emptyPanelPayload(input)));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'D:/Bolt/Bolt' }));

    render(<App fetcher={fetcher} />);
    await settleNetwork(fetcher);
    fireEvent.change(screen.getByLabelText('任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始任务' }));
    expect(await screen.findByText('run_43')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('输入任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '创建闭环任务' }));
    expect(await screen.findByText('当前闭环：cl_43')).toBeInTheDocument();
    expect(requests[0].body).toMatchObject({ objective: '修复拼写错误', template_id: 'bugfix', run_id: 'run_43' });

    fireEvent.click(screen.getByRole('button', { name: '绑定当前运行' }));
    expect(await screen.findByText('已绑定运行：run_43')).toBeInTheDocument();
    expect(requests[1].body).toEqual({ run_id: 'run_43' });

    fireEvent.click(screen.getByRole('button', { name: '刷新闭环状态' }));
    expect(await screen.findByText('等待人工批准')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /push|release|delete|approve/i })).not.toBeInTheDocument();
  });
});

function closure(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cl_43',
    objective: '修复拼写错误',
    template_id: 'bugfix',
    run_id: null,
    goal_id: null,
    status: 'pending',
    final_status: 'pending',
    plan_summary: '',
    changed_files: [],
    commands: [],
    command_results: [],
    permission_request_ids: [],
    retry_count: 0,
    review_summary: '',
    next_action: '',
    created_at: 0,
    ...overrides,
  };
}
