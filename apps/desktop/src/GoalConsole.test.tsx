/**
 * M37 + M38 Goal Console — desktop long-task cockpit + resume diagnostics tests.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GoalConsole } from './GoalConsole';
import type { Goal, GoalEvidence, TimelineEvent } from '@bolt/shared/autonomy';
import type { AgentLoopResult } from '@bolt/shared';

const baseGoal: Goal = {
  id: 'goal_test1234', objective: '修复 README 中的拼写错误',
  criteria: ['所有拼写已修正'], status: 'pending',
  max_steps: 10, max_cost: 5.0, max_wall_time: 300,
  workspace: 'D:/Projects/Bolt', step_count: 0,
};

const noopApi = {
  createGoal: vi.fn().mockResolvedValue(baseGoal),
  startRun: vi.fn().mockResolvedValue({ id: 'run_noop' }),
  runAgentLoop: vi.fn().mockResolvedValue({ status: 'executed', steps: 0 }),
  pauseGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }),
  resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }),
  clearGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'stopped' }),
  getGoal: vi.fn().mockResolvedValue(baseGoal),
  fetchGoalEvidence: vi.fn().mockResolvedValue([]),
  fetchRunTimeline: vi.fn().mockResolvedValue([]),
};

describe('M37 Goal Console', () => {
  it('disables start when no workspace, enables when objective >= 5 + workspace', () => {
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} />);
    expect(screen.getByRole('button', { name: '开始长任务' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
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
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status: 'paused' }} api={noopApi} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeInTheDocument();
  });

  it('shows step count progress', () => {
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status: 'running', step_count: 5 }} api={noopApi} />);
    expect(screen.getByText('5 / 10')).toBeInTheDocument();
  });

  it('calls createGoal + startRun + runAgentLoop, shows running', async () => {
    const loopResult: AgentLoopResult = { status: 'executed', steps: 3 };
    const api = { ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }), startRun: vi.fn().mockResolvedValue({ id: 'run_auto1' }), runAgentLoop: vi.fn().mockResolvedValue(loopResult) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalled());
    expect(screen.getByText('运行中')).toBeInTheDocument();
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
  });

  it('calls pauseGoal on 暂停任务 click', async () => {
    const api = { ...noopApi, pauseGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status: 'running' }} api={api} />);
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

  it('does not call runAgentLoop when resumeGoal returns paused (normal resume blocked)', async () => {
    const api = {
      ...noopApi,
      resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }),
      runAgentLoop: vi.fn().mockResolvedValue({ status: 'executed', steps: 3 }),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status: 'paused' }} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    await vi.waitFor(() => expect(api.resumeGoal).toHaveBeenCalled());
    expect(api.runAgentLoop).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText('恢复被阻止，请检查工作区冲突')).toBeInTheDocument());
  });
});

describe('M38 Goal Resume & Diagnostics', () => {
  it('shows 发现未完成长任务 banner with id/objective/status/step_count', () => {
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('发现未完成长任务')).toBeInTheDocument();
    expect(screen.getByText('goal_test1234')).toBeInTheDocument();
    expect(screen.getByText('修复 README 中的拼写错误')).toBeInTheDocument();
    expect(screen.getByText('已暂停')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('does not auto-resume; calls resumeGoal + startRun + runAgentLoop on 恢复任务 click', async () => {
    const api = {
      ...noopApi,
      resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'running' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_resume38' }),
      runAgentLoop: vi.fn().mockResolvedValue({ status: 'executed', steps: 4 }),
    };
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    expect(api.runAgentLoop).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    await vi.waitFor(() => expect(api.resumeGoal).toHaveBeenCalled());
    await vi.waitFor(() => expect(api.startRun).toHaveBeenCalled());
    await vi.waitFor(() => expect(api.runAgentLoop).toHaveBeenCalledWith('http://core', 'run_resume38', 10));
  });

  it('does not call startRun/runAgentLoop when resumeGoal returns paused (blocked)', async () => {
    const api = {
      ...noopApi,
      resumeGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'paused' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_blocked' }),
      runAgentLoop: vi.fn().mockResolvedValue({ status: 'executed', steps: 4 }),
    };
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    fireEvent.click(screen.getByRole('button', { name: '恢复任务' }));
    await vi.waitFor(() => expect(api.resumeGoal).toHaveBeenCalled());
    expect(api.startRun).not.toHaveBeenCalled();
    expect(api.runAgentLoop).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText('恢复被阻止，请检查工作区冲突')).toBeInTheDocument());
  });

  it('shows 等待人工批准 for paused unfinished goal', () => {
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByText('等待人工批准')).toBeInTheDocument();
  });

  it('shows 失败 + suggestion for failed, 已停止 + 已达到最大步数 for maxed', () => {
    const { unmount } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[{ ...baseGoal, status: 'failed', step_count: 5 }]} />);
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('建议：检查错误日志后重新创建任务')).toBeInTheDocument();
    unmount();
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={[{ ...baseGoal, status: 'stopped', step_count: 10 }]} />);
    expect(screen.getByText('已停止')).toBeInTheDocument();
    expect(screen.getByText('已达到最大步数')).toBeInTheDocument();
  });

  it('disables 恢复任务 when no workspace', () => {
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    expect(screen.getByRole('button', { name: '恢复任务' })).toBeDisabled();
  });

  it('no ipcRenderer/shell/process/fs in resume UI', () => {
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    const { container } = render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={noopApi} unfinishedGoals={unfinished} />);
    const html = container.innerHTML;
    expect(html).not.toContain('ipcRenderer');
    expect(html).not.toContain('shell');
    expect(html).not.toContain('process.');
  });

  it('fetches evidence via useEffect for unfinished goal', async () => {
    const evidence: GoalEvidence[] = [{ phase: 'test', action: 'pytest', result: 'pass', summary: '299 ok' }];
    const api = { ...noopApi, fetchGoalEvidence: vi.fn().mockResolvedValue(evidence) };
    const unfinished = [{ ...baseGoal, status: 'paused', step_count: 3 }];
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} unfinishedGoals={unfinished} />);
    await waitFor(() => expect(api.fetchGoalEvidence).toHaveBeenCalledWith('http://core', 'goal_test1234'));
    expect(screen.getByText('1 条证据')).toBeInTheDocument();
    expect(screen.getByText('299 ok')).toBeInTheDocument();
  });

  it('does not show timeline when goal has no runId (no startRun yet)', async () => {
    const api = { ...noopApi, fetchRunTimeline: vi.fn().mockResolvedValue([]), fetchGoalEvidence: vi.fn().mockResolvedValue([]) };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={{ ...baseGoal, status: 'running' }} api={api} />);
    await waitFor(() => expect(api.fetchGoalEvidence).toHaveBeenCalled());
    // No runId → timeline not fetched, not rendered
    expect(api.fetchRunTimeline).not.toHaveBeenCalled();
    expect(screen.queryByText('暂无长任务记录')).not.toBeInTheDocument();
  });

  it('shows timeline count after startRun completes', async () => {
    const timeline: TimelineEvent[] = Array.from({ length: 8 }, (_, i) => ({ type: `event.${i}`, sequence: i + 1, payload: {} }));
    const api = {
      ...noopApi, createGoal: vi.fn().mockResolvedValue({ ...baseGoal, status: 'pending' }),
      startRun: vi.fn().mockResolvedValue({ id: 'run_tl1' }),
      runAgentLoop: vi.fn().mockResolvedValue({ status: 'executed', steps: 3 }),
      fetchRunTimeline: vi.fn().mockResolvedValue(timeline),
      fetchGoalEvidence: vi.fn().mockResolvedValue([]),
    };
    render(<GoalConsole workspacePath="D:/Projects/Bolt" goal={null} api={api} />);
    fireEvent.change(screen.getByLabelText('长任务目标'), { target: { value: '修复拼写错误' } });
    fireEvent.click(screen.getByRole('button', { name: '开始长任务' }));
    await waitFor(() => expect(api.fetchRunTimeline).toHaveBeenCalledWith('http://core', 'run_tl1'));
    await waitFor(() => expect(screen.getByText('8 条记录')).toBeInTheDocument());
  });
});
