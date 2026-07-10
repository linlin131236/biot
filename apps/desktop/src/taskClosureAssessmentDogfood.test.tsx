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

describe('M44 task closure assessment dogfood', () => {
  it('creates closure, binds run, updates assessment, and shows Chinese evidence status', async () => {
    const urls: string[] = [];
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      urls.push(input);
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/goals/unfinished')) return Promise.resolve(json([]));
      if (input.endsWith('/harness/runs') && init?.method === 'POST') return Promise.resolve(json({ id: 'run_44', workspace: 'D:/Bolt/Bolt' }));
      if (input.endsWith('/task-closures') && init?.method === 'POST') return Promise.resolve(json(closure({ id: 'cl_44', run_id: 'run_44' })));
      if (input.endsWith('/task-closures/cl_44/bind-run') && init?.method === 'POST') return Promise.resolve(json(closure({ id: 'cl_44', run_id: 'run_44' })));
      if (input.endsWith('/task-closures/cl_44/verification-plan')) return Promise.resolve(json({ template_id: 'bugfix', checks: [{ id: 'quality', label: '测试或质量门证据', command: 'pytest', required: true, satisfied: false, evidence: '', missing_reason: '缺少测试证据' }] }));
      if (input.endsWith('/task-closures/cl_44/assessment') && init?.method === 'POST') return Promise.resolve(json(closure({ id: 'cl_44', run_id: 'run_44', next_action: '缺少验证证据' })));
      if (input.endsWith('/task-closures/cl_44/assessment')) return Promise.resolve(json({ status: 'missing_evidence', summary: '缺少验证证据', missing: ['缺少测试证据'], repair_suggestions: ['补充缺少的验证证据后重新评估完成度'] }));
      if (input.endsWith('/execution-queue?closure_id=cl_44')) return Promise.resolve(json([queueItem()]));
      if (input.endsWith('/task-closures/cl_44/execution-queue/propose') && init?.method === 'POST') return Promise.resolve(json([queueItem()]));
      if (input.endsWith('/execution-queue/eq_44/approve') && init?.method === 'POST') return Promise.resolve(json(queueItem({ status: 'approved' })));
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
    expect(await screen.findByText('run_44')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('输入任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '创建闭环任务' }));
    expect(await screen.findByText('验证计划')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '绑定当前运行' }));
    expect(await screen.findByText('已绑定运行：run_44')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '评估完成度' }));
    expect(await screen.findByText('缺少证据')).toBeInTheDocument();
    expect(screen.getByText(/建议修复：/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '生成待处理动作' }));
    expect(await screen.findByText('记录验证命令')).toBeInTheDocument();
    expect(screen.getAllByText('命令建议：pytest（不执行命令）').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '批准' }));
    expect(await screen.findByText('已批准')).toBeInTheDocument();
    expect(urls.some(url => url.includes('agent-loops'))).toBe(false);
    expect(urls.some(url => url.includes('/permissions/') && url.includes('/approve'))).toBe(false);
    expect(urls.some(url => url.includes('delete'))).toBe(false);
    expect(urls.some(url => url.includes('push'))).toBe(false);
  });
});

function queueItem(overrides: Record<string, unknown> = {}) {
  return {
    id: 'eq_44',
    closure_id: 'cl_44',
    kind: 'verification_command',
    title: '记录验证命令',
    description: '缺少测试证据',
    risk: 'verification_command',
    status: 'pending',
    command: 'pytest',
    reason: '',
    result: '',
    created_at: 0,
    ...overrides,
  };
}

function closure(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cl_44',
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
