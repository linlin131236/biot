import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';

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
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
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
    expect(urls.some(url => url.includes('approve'))).toBe(false);
    expect(urls.some(url => url.includes('agent-loops'))).toBe(false);
    expect(urls.some(url => url.includes('delete'))).toBe(false);
    expect(urls.some(url => url.includes('push'))).toBe(false);
  });
});

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
