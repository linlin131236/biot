/**
 * M37 Goal Console — desktop long-task cockpit dogfood tests.
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
