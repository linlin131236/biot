/**
 * M37 + M38 Goal Console — desktop long-task cockpit + resume diagnostics tests.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { GoalConsole } from './GoalConsole';
import type { Goal } from '@bolt/shared/autonomy';
import type { AgentLoopResult } from '@bolt/shared';

const baseGoal: Goal = {
  id: 'goal_test1234',
  objective: '修复 README 中的拼写错误',
  criteria: ['所有拼写已修正'],
  status: 'pending',
  max_steps: 10,
  max_cost: 5.0,
  max_wall_time: 300,
  workspace: 'D:/Projects/Bolt',
  step_count: 0,
};

const noopApi = {
  createGoal: vi.fn(), startRun: vi.fn(), runAgentLoop: vi.fn(),
  pauseGoal: vi.fn(), resumeGoal: vi.fn(), clearGoal: vi.fn(),
  getGoal: vi.fn(), fetchGoalEvidence: vi.fn(), fetchRunTimeline: vi.fn(),
};

describe('M37 Goal Console', () => {
  it('disables start button when no workspace, enables when objective >= 5 chars', () => {
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} />);
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    // still disabled without workspace
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
  });

  it('enables start when workspace + objective >= 5', () => {
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    expect(screen.getByRole('button', { name: '开始长任务' })).not.toBeDisabled();
  });

  it('displays status labels: 运行中/已暂停/已停止/已拒绝', () => {
    const statuses: [Goal['status'], string][] = [
      ['running', '运行中'], ['paused', '已暂停'], ['stopped', '已停止'], ['rejected', '已拒绝'],
    ];
    for (const [status, label] of statuses) {
      const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status }} api={noopApi} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('shows 等待人工批准 for paused, 已达到最大步数 for maxed', () => {
    const paused = { ...baseGoal, status: 'paused' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={paused} api={noopApi} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeInTheDocument();

    const maxed = { ...baseGoal, status: 'stopped' as const, step_count: 10 };
    const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={maxed} api={noopApi} />);
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
    unmount();
  });

  it('shows step count progress', () => {
    const running = { ...baseGoal, status: 'running' as const, step_count: 5 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={noopApi} />);
    expect(screen.getByText('5 / 10')).toBeInTheDocument();
  });

  it('calls createGoal + startRun + runAgentLoop, shows running from loop result', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 3 };
    const api = { ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }), startRun: vi.fn().mockResolvedValue({ id: 'run_auto1' }), runAgentLoop: vi.fn().mockResolvedValue(loopResult) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('运行中')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('shows 等待人工批准 when loop returns pending_permission', async () => {
    const loopResult: AgentLoopResult = { status: 'pending_permission', steps: 2 };
    const api = { ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }), startRun: vi.fn().mockResolvedValue({ id: 'run_auto2' }), runAgentLoop: vi.fn().mockResolvedValue(loopResult) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('shows 失败 + error when loop returns failed', async () => {
    const loopResult: AgentLoopResult = { status: 'failed', steps: 1, error: 'OOM' };
    const api = { ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }), startRun: vi.fn().mockResolvedValue({ id: 'run_auto3' }), runAgentLoop: vi.fn().mockResolvedValue(loopResult) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('OOM')).toBeInTheDocument();
  });

  it('shows 已停止 + 已达到最大步数 when loop hits max_steps', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 10 };
    const api = { ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }), startRun: vi.fn().mockResolvedValue({ id: 'run_max1' }), runAgentLoop: vi.fn().mockResolvedValue(loopResult) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} maxSteps={10} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('已停止')).toBeInTheDocument();
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
    expect(screen.getByText('10 / 10')).toBeInTheDocument();
  });

  it('calls pauseGoal/resumeGoal/clearGoal on button clicks', async () => {
    const api = { ...noopApi, pauseGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }), resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }), clearGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'stopped' }) };
    const running = { ...baseGoal, status: 'running' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '暂停任务' }));
    expect(api.pauseGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('no ipcRenderer/shell/process/fs in rendered HTML', () => {
    const { container } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={baseGoal} api={noopApi} />);
    const html = container.innerHTML;
    expect(html).not.toContain('ipcRenderer');
    expect(html).not.toContain('process.');
    expect(html).not.toContain('shell');
  });
});

describe('M38 Goal Resume & Diagnostics', () => {
  it('shows 发现未完成长任务 banner with goal id/objective/status/step_count', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('发现未完成长任务')).toBeInTheDocument();
    expect(screen.getByText('goal_test1234')).toBeInTheDocument();
    expect(screen.getByText('修复 README 中的拼写错误')).toBeInTheDocument();
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('does not auto-resume on load; calls resumeGoal on 恢复任务 click', async () => {
    const api = { ...noopApi, resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }) };
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    expect(api.runAgentLoop).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    expect(api.resumeGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('shows 等待人工批准 for paused unfinished goal', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('shows 失败 + suggestion for failed, 已停止 + 已达到最大步数 for maxed', () => {
    const failedGoal = { ...baseGoal, status: 'failed' as const, step_count: 5 };
    const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[failedGoal]} />);
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('建议：检查错误日志后重新创建任务')).toBeInTheDocument();
    unmount();

    const maxedGoal = { ...baseGoal, status: 'stopped' as const, step_count: 10 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[maxedGoal]} />);
    expect(screen.getByText('已停止')).toBeInTheDocument();
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
  });

  it('disables 恢复任务 when no workspace', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeDisabled();
  });

  it('no ipcRenderer/shell/process/fs in resume UI', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const { container } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    const html = container.innerHTML;
    expect(html).not.toContain('ipcRenderer');
    expect(html).not.toContain('shell');
    expect(html).not.toContain('process.');
  });

  it('shows 暂无长任务记录 when timeline empty, count when has events', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={[]} />);
    expect(screen.getByText('暂无长任务记录')).toBeInTheDocument();
    unmount();

    const timeline = [{ type: 'run.created', sequence: 1, payload: {} }, { type: 'tool.requested', sequence: 2, payload: {} }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={timeline} />);
    expect(screen.getByText('2 条记录')).toBeInTheDocument();
  });

  it('shows 暂无证据 when evidence empty, count + summary when has records', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} evidence={[]} />);
    expect(screen.getByText('暂无证据')).toBeInTheDocument();
    unmount();

    const evidence = [{ phase: 'test', action: 'pytest', result: 'pass', summary: '299 ok' }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} evidence={evidence} />);
    expect(screen.getByText('1 条证据')).toBeInTheDocument();
  });
});
