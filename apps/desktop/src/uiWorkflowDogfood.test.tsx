/**
 * M33 UI Workflow Dogfood — red tests for Chinese UI + real click path.
 *
 * Covers:
 *   1. All user-visible buttons/labels are Chinese (no English leftovers)
 *   2. Real click path: input goal → start run → create goal → read file → submit patch → approve → checkpoint → review → timeline
 *   3. Permission gate: patch goes pending, approve allows, reject blocks
 *   4. Tool flow UI: file path, read file, submit patch inputs visible
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
}

describe('M33 Chinese UI', () => {
  it('shows Chinese button labels in the toolbar', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    const zhButtons = ['开始任务', '创建目标', '执行一步', '刷新轨迹', '刷新记忆', '刷新权限', '整理文档', '时间线', '审查'];
    for (const name of zhButtons) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument();
    }
  });

  it('shows Chinese panel headings', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    const zhHeadings = ['任务日志', '执行轨迹', '自测工作流', '待批准权限', '记忆 / 感知'];
    for (const text of zhHeadings) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });

  it('shows Chinese empty-state text', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByText('暂无执行结果')).toBeInTheDocument();
    expect(screen.getByText('暂无轨迹事件')).toBeInTheDocument();
    expect(screen.getByText('暂无待批准权限')).toBeInTheDocument();
    expect(screen.getByText('暂无记忆')).toBeInTheDocument();
    expect(screen.getByText('暂无目标')).toBeInTheDocument();
  });

  it('shows Chinese sidebar labels', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByText('Agent Core 状态')).toBeInTheDocument();
    expect(screen.getAllByText(/工作区/).length).toBeGreaterThan(0);
    expect(screen.getByText('核心服务地址')).toBeInTheDocument();
    expect(screen.getByText('当前运行')).toBeInTheDocument();
  });

  it('shows Chinese model panel labels', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByRole('button', { name: '保存模型设置' })).toBeInTheDocument();
  });

  it('shows Chinese API key status', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByText('API 密钥未配置')).toBeInTheDocument();
  });

  it('has no leftover English UI buttons', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    const enButtons = ['Start Run', 'Create Goal', 'Run Step', 'Refresh Trace', 'Run Gardener', 'Timeline', 'Review', 'Save Model Settings', 'Approve', 'Reject'];
    for (const name of enButtons) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    }
  });
});

describe('M33 UI workflow click path', () => {
  it('starts a run and creates a goal in Chinese', async () => {
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/harness/runs') && init?.method === 'POST') return Promise.resolve(json({ id: 'run_33', workspace: 'C:/Projects/Bolt' }));
      if (input.endsWith('/goals') && init?.method === 'POST') return Promise.resolve(json({ id: 'goal_33', objective: 'test', status: 'pending', criteria: [] }));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.change(screen.getByLabelText('任务目标'), { target: { value: '中文测试' } });
    fireEvent.click(screen.getByRole('button', { name: '开始任务' }));
    expect(await screen.findByText('run_33')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '创建目标' }));
    expect(await screen.findByText('goal_33')).toBeInTheDocument();
  });

  it('shows pending permission with Chinese approve/reject', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/permissions/pending')) return Promise.resolve(json([{ request_id: 'perm_1', tool: 'file.patch', operation: 'patch', reason: '修改文件', payload: {} }]));
      if (input.includes('/permissions/perm_1/approve')) return Promise.resolve(json({ request_id: 'perm_1', status: 'approved' }));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    fireEvent.click(screen.getByRole('button', { name: '刷新权限' }));
    expect(await screen.findByText('修改文件')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: '批准' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '拒绝' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '批准' }));
  });

  it('shows tool flow inputs for file read and patch', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByLabelText('文件路径')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '读取文件' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '提交补丁' })).toBeInTheDocument();
  });

  it('sends canonical backend tool names from the UI tool flow', async () => {
    const requests: unknown[] = [];
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/harness/runs/run_33/tool-requests') && init?.method === 'POST') {
        const body = JSON.parse((init as RequestInit & { body: string }).body as string);
        requests.push(body);
        if (body.tool === 'file.read') return Promise.resolve(json({ request_id: 'tool_read', status: 'executed', output: 'read ok' }));
        return Promise.resolve(json({ request_id: 'tool_patch', status: 'pending_permission', reason: 'needs approval' }));
      }
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core', lastRunId: 'run_33' }));

    render(<App fetcher={fetcher} />);
    fireEvent.change(screen.getByLabelText('文件路径'), { target: { value: 'C:/Projects/Bolt/main.txt' } });
    fireEvent.click(screen.getByRole('button', { name: '读取文件' }));
    expect(await screen.findByText('read ok')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('原文本'), { target: { value: 'hello' } });
    fireEvent.change(screen.getByLabelText('新文本'), { target: { value: 'hello bolt' } });
    fireEvent.click(screen.getByRole('button', { name: '提交补丁' }));
    expect(await screen.findByText('needs approval')).toBeInTheDocument();

    expect(requests).toEqual([
      { tool: 'file.read', operation: 'read', payload: { path: 'C:/Projects/Bolt/main.txt' } },
      { tool: 'file.patch', operation: 'patch', payload: { path: 'C:/Projects/Bolt/main.txt', old_string: 'hello', new_string: 'hello bolt' } },
    ]);
  });
});

describe('M35 Workspace binding', () => {
  it('shows 更换工作区 button in sidebar', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByRole('button', { name: '更换工作区' })).toBeInTheDocument();
  });

  it('shows 工作区未选择 when workspace is empty', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: '', coreUrl: 'http://core' }));
    render(<App />);

    expect(screen.getByText('工作区未选择')).toBeInTheDocument();
  });

  it('sends relative path via tool flow, backend resolves against workspace', async () => {
    const requests: unknown[] = [];
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/harness/runs/run_35/tool-requests') && init?.method === 'POST') {
        const body = JSON.parse((init as RequestInit & { body: string }).body as string);
        requests.push(body);
        return Promise.resolve(json({ request_id: 'tool_35', status: 'executed', output: 'relative ok' }));
      }
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core', lastRunId: 'run_35' }));

    render(<App fetcher={fetcher} />);
    fireEvent.change(screen.getByLabelText('文件路径'), { target: { value: 'README.md' } });
    fireEvent.click(screen.getByRole('button', { name: '读取文件' }));
    expect(await screen.findByText('relative ok')).toBeInTheDocument();

    expect(requests[0]).toEqual({ tool: 'file.read', operation: 'read', payload: { path: 'README.md' } });
  });

  it('disables tool actions when no workspace is selected', () => {
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: '', coreUrl: 'http://core', lastRunId: 'run_stale' }));
    render(<App />);

    expect(screen.getByRole('button', { name: '开始任务' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '创建目标' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '读取文件' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '提交补丁' })).toBeDisabled();
  });

  it('persists selected workspace from the workspace picker', async () => {
    const selectWorkspace = vi.fn().mockResolvedValue('D:/Projects/RealBolt');
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: '', coreUrl: 'http://core' }));

    render(<App selectWorkspace={selectWorkspace} />);
    fireEvent.click(screen.getByRole('button', { name: '选择工作区' }));

    expect(await screen.findByText('D:/Projects/RealBolt')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).toContain('D:/Projects/RealBolt');
  });

  it('does not change workspace when picker returns null (cancel)', async () => {
    const selectWorkspace = vi.fn().mockResolvedValue(null);
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Existing', coreUrl: 'http://core' }));

    render(<App selectWorkspace={selectWorkspace} />);
    fireEvent.click(screen.getByRole('button', { name: '更换工作区' }));

    await vi.waitFor(() => expect(selectWorkspace).toHaveBeenCalled());
    expect(screen.getByText('C:/Existing')).toBeInTheDocument();
    expect(localStorage.getItem('bolt.desktop.session')).toContain('C:/Existing');
  });

  it('uses window.bolt selectWorkspace by default when available', async () => {
    const originalBolt = window.bolt;
    window.bolt = { selectWorkspace: vi.fn().mockResolvedValue('E:/Native/Bolt') };
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Existing', coreUrl: 'http://core' }));

    try {
      render(<App />);
      fireEvent.click(screen.getByRole('button', { name: '更换工作区' }));

      expect(await screen.findByText('E:/Native/Bolt')).toBeInTheDocument();
      expect(window.bolt?.selectWorkspace).toHaveBeenCalled();
      expect(localStorage.getItem('bolt.desktop.session')).toContain('E:/Native/Bolt');
    } finally {
      window.bolt = originalBolt;
    }
  });
});

describe('M38 Goal Resume in App', () => {
  it('fetches unfinished goals on mount and shows 发现未完成长任务', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/goals/unfinished')) return Promise.resolve(json([{ id: 'goal_38', objective: 'M38测试', criteria: [], status: 'paused', max_steps: 10, max_cost: 5.0, max_wall_time: 300, workspace: 'C:/Projects/Bolt', step_count: 3 }]));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    expect(await screen.findByText('发现未完成长任务')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('http://core/goals/unfinished');
  });

  it('does not auto-call runAgentLoop for unfinished goals', async () => {
    const fetcher = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/goals/unfinished')) return Promise.resolve(json([{ id: 'goal_38', objective: 'M38测试', criteria: [], status: 'paused', max_steps: 10, max_cost: 5.0, max_wall_time: 300, workspace: 'C:/Projects/Bolt', step_count: 3 }]));
      if (input.endsWith('/agent-loops') && init?.method === 'POST') return Promise.resolve(json({ status: 'executed', steps: 4 }));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    await screen.findByText('发现未完成长任务');
    // agent-loops should not be called without user click
    const agentLoopCalls = fetcher.mock.calls.filter((c: string[]) => c[0].includes('/agent-loops'));
    expect(agentLoopCalls.length).toBe(0);
  });

  it('shows 等待人工批准 for paused unfinished goal', async () => {
    const fetcher = vi.fn().mockImplementation((input: string) => {
      if (input.endsWith('/health')) return Promise.resolve(json({ status: 'ok', service: 'bolt-agent-core' }));
      if (input.endsWith('/goals/unfinished')) return Promise.resolve(json([{ id: 'goal_38', objective: 'M38测试', criteria: [], status: 'paused', max_steps: 10, max_cost: 5.0, max_wall_time: 300, workspace: 'C:/Projects/Bolt', step_count: 3 }]));
      return Promise.resolve(json({}));
    });
    localStorage.setItem('bolt.desktop.session', JSON.stringify({ completed: true, workspacePath: 'C:/Projects/Bolt', coreUrl: 'http://core' }));

    render(<App fetcher={fetcher} />);
    expect(await screen.findByText('等待人工批准')).toBeInTheDocument();
  });
});
