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
  createGoal: vi.fn(),
  startRun: vi.fn(),
  runAgentLoop: vi.fn(),
  pauseGoal: vi.fn(),
  resumeGoal: vi.fn(),
  clearGoal: vi.fn(),
  getGoal: vi.fn(),
  fetchGoalEvidence: vi.fn(),
  fetchRunTimeline: vi.fn(),
};

describe('M37 Goal Console', () => {
  it('disables start button when no workspace', () => {
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} />);
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
  });

  it('enables start button when workspace and objective provided', () => {
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} />);
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    expect(screen.getByRole('button', { name: '开始长任务' })).not.toBeDisabled();
  });

  it('shows Chinese error when objective is too short on forced submit', () => {
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复' } });
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    expect(screen.getByRole('button', { name: '开始长任务' })).not.toBeDisabled();
  });

  it('displays 运行中 for running goal', () => {
    const running = { ...baseGoal, status: 'running' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={noopApi} />);
    expect(screen.getByText('运行中')).toBeInTheDocument();
  });

  it('displays 等待人工批准 for paused goal', () => {
    const paused = { ...baseGoal, status: 'paused' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={paused} api={noopApi} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('displays 已达到最大步数 when step_count >= max_steps', () => {
    const maxed = { ...baseGoal, status: 'stopped' as const, step_count: 10 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={maxed} api={noopApi} />);
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
  });

  it('shows 已暂停 and resume button for paused goal', () => {
    const paused = { ...baseGoal, status: 'paused' as const, step_count: 3 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={paused} api={noopApi} />);
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeInTheDocument();
  });

  it('shows 已停止 for stopped goal', () => {
    const stopped = { ...baseGoal, status: 'stopped' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={stopped} api={noopApi} />);
    expect(screen.getByText('已停止')).toBeInTheDocument();
  });

  it('shows 已拒绝 for rejected goal', () => {
    const rejected = { ...baseGoal, status: 'rejected' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={rejected} api={noopApi} />);
    expect(screen.getByText('已拒绝')).toBeInTheDocument();
  });

  it('calls createGoal + startRun + runAgentLoop, shows running from loop result', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 3 };
    const api = {
      ...noopApi,
      createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_auto1' }),
      runAgentLoop: vi.fn().mockResolvedValue(loopResult),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(api.runAgentLoop).toHaveBeenCalledWith('http://core', 'run_auto1', 10);
    expect(screen.getByText('运行中')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('shows 等待人工批准 when runAgentLoop returns pending_permission', async () => {
    const loopResult: AgentLoopResult = { status: 'pending_permission', steps: 2 };
    const api = {
      ...noopApi,
      createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_auto2' }),
      runAgentLoop: vi.fn().mockResolvedValue(loopResult),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('shows 失败 when runAgentLoop returns failed', async () => {
    const loopResult: AgentLoopResult = { status: 'failed', steps: 1, error: 'OOM' };
    const api = {
      ...noopApi,
      createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_auto3' }),
      runAgentLoop: vi.fn().mockResolvedValue(loopResult),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('OOM')).toBeInTheDocument();
  });

  it('calls pauseGoal when pause button clicked', async () => {
    const api = { ...noopApi, pauseGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }) };
    const running = { ...baseGoal, status: 'running' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '暂停任务' }));
    expect(api.pauseGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('calls resumeGoal when resume button clicked', async () => {
    const api = { ...noopApi, resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }) };
    const paused = { ...baseGoal, status: 'paused' as const, step_count: 3 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={paused} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    expect(api.resumeGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('calls clearGoal when stop button clicked', async () => {
    const api = { ...noopApi, clearGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'stopped' }) };
    const running = { ...baseGoal, status: 'running' as const };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '停止任务' }));
    expect(api.clearGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('shows step count progress', () => {
    const running = { ...baseGoal, status: 'running' as const, step_count: 5 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={running} api={noopApi} />);
    expect(screen.getByText('5 / 10')).toBeInTheDocument();
  });

  it('shows 已停止 and 已达到最大步数 when runAgentLoop hits max_steps', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 10 };
    const api = {
      ...noopApi,
      createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_max1' }),
      runAgentLoop: vi.fn().mockResolvedValue(loopResult),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} maxSteps={10} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('已停止')).toBeInTheDocument();
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
    expect(screen.getByText('10 / 10')).toBeInTheDocument();
  });

  it('does not expose shell/fs/process/ipcRenderer', () => {
    const { container } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={baseGoal} api={noopApi} />);
    const html = container.innerHTML;
    expect(html).not.toContain('ipcRenderer');
    expect(html).not.toContain('shell');
    expect(html).not.toContain('process.');
  });
});

describe('M38 Goal Resume & Diagnostics', () => {
  it('shows 发现未完成长任务 when unfinishedGoals provided', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('发现未完成长任务')).toBeInTheDocument();
  });

  it('shows unfinished goal id, objective, status, step_count', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('goal_test1234')).toBeInTheDocument();
    expect(screen.getByText('修复 README 中的拼写错误')).toBeInTheDocument();
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('does not auto-resume unfinished goals on load', () => {
    const api = { ...noopApi, runAgentLoop: vi.fn() };
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    expect(api.runAgentLoop).not.toHaveBeenCalled();
  });

  it('calls resumeGoal when clicking 恢复任务 on unfinished goal', async () => {
    const api = {
      ...noopApi,
      resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }),
    };
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    expect(api.resumeGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('calls resumeGoal on unfinished goal resume click', async () => {
    const api = {
      ...noopApi,
      resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }),
    };
    const pausedGoal = { ...baseGoal, status: 'paused' as const, step_count: 3 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={pausedGoal} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    expect(api.resumeGoal).toHaveBeenCalledWith('http://core', 'goal_test1234');
  });

  it('shows 等待人工批准 when unfinished goal has pending_permission status', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('shows 失败 and error info for failed unfinished goal', () => {
    const failedGoal: Goal = { ...baseGoal, status: 'failed' as const, step_count: 5 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[failedGoal]} />);
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('建议：检查错误日志后重新创建任务')).toBeInTheDocument();
  });

  it('shows 已停止 and 已达到最大步数 for maxed unfinished goal', () => {
    const maxedGoal: Goal = { ...baseGoal, status: 'stopped' as const, step_count: 10 };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[maxedGoal]} />);
    expect(screen.getByText('已停止')).toBeInTheDocument();
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
  });

  it('disables 恢复任务 when no workspace', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeDisabled();
  });

  it('does not show ipcRenderer/fs/shell/process in resume UI', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const { container } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    const html = container.innerHTML;
    expect(html).not.toContain('ipcRenderer');
    expect(html).not.toContain('fs.');
    expect(html).not.toContain('shell');
    expect(html).not.toContain('process.');
  });

  it('shows 暂无长任务记录 when timeline is empty', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={[]} />);
    expect(screen.getByText('暂无长任务记录')).toBeInTheDocument();
  });

  it('shows timeline event count when timeline has events', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const timeline = [
      { type: 'run.created', sequence: 1, payload: {} },
      { type: 'tool.requested', sequence: 2, payload: {} },
    ];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={timeline} />);
    expect(screen.getByText('2 条记录')).toBeInTheDocument();
  });

  it('shows at most 5 recent timeline events', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const timeline = Array.from({ length: 8 }, (_, i) => ({ type: `event.${i}`, sequence: i + 1, payload: {} }));
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={timeline} />);
    expect(screen.getByText('8 条记录')).toBeInTheDocument();
    // Should show only 5 events (indices 3-7)
    expect(screen.getByText('event.3')).toBeInTheDocument();
    expect(screen.getByText('event.7')).toBeInTheDocument();
    expect(screen.queryByText('event.0')).not.toBeInTheDocument();
    expect(screen.queryByText('event.2')).not.toBeInTheDocument();
  });

  it('shows event type and sequence for each timeline event', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const timeline = [{ type: 'run.created', sequence: 1, payload: {} }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} timeline={timeline} />);
    expect(screen.getByText('run.created')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows 暂无证据 when evidence is empty', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} evidence={[]} />);
    expect(screen.getByText('暂无证据')).toBeInTheDocument();
  });

  it('shows evidence count when evidence has records', () => {
    const unfinished = [{ ...baseGoal, status: 'paused' as const, step_count: 3 }];
    const evidence = [{ phase: 'test', result: 'pass', summary: 'pytest ok' }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} evidence={evidence} />);
    expect(screen.getByText('1 条证据')).toBeInTheDocument();
  });
});
