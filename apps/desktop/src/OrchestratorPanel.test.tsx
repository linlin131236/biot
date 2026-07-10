/**
 * OrchestratorPanel tests (M163).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { OrchestratorPanel } from './OrchestratorPanel';

function fakeApi(rolesData: Record<string, unknown> = { roles: [
  { role_key: 'planner', label_cn: '规划师', status: 'ready' },
  { role_key: 'researcher', label_cn: '研究员', status: 'ready' },
  { role_key: 'builder', label_cn: '构建师', status: 'ready' },
  { role_key: 'reviewer', label_cn: '审查员', status: 'ready' },
  { role_key: 'skill_learner', label_cn: '技能学习器', status: 'ready' },
]}, resultData: Record<string, unknown> = { task_description: 't', rounds: 1, final_verdict: 'approved', builder_output: { summary: 's' }, review_findings: [], proposals: [], trace: [] }) {
  return {
    runOrchestration: vi.fn().mockResolvedValue(resultData),
    fetchRoles: vi.fn().mockResolvedValue(rolesData),
  };
}

describe('OrchestratorPanel', () => {
  it('renders title and 5 roles', async () => {
    render(<OrchestratorPanel api={fakeApi()} />);
    expect(screen.getByText('编排器')).toBeTruthy();
    expect(screen.getByText('串联 5 个角色：规划师 → 研究员 → 构建师 → 审查员 → 技能学习器')).toBeTruthy();
    expect(await screen.findByText('规划师')).toBeTruthy();
    expect(await screen.findByText('研究员')).toBeTruthy();
    expect(await screen.findByText('构建师')).toBeTruthy();
    expect(await screen.findByText('审查员')).toBeTruthy();
    expect(await screen.findByText('技能学习器')).toBeTruthy();
  });

  it('runs orchestration and shows pipeline trace', async () => {
    const api = fakeApi();
    const resultData = {
      task_description: '任务',
      rounds: 2,
      final_verdict: 'approved',
      builder_output: { summary: '构建摘要' },
      review_findings: [],
      proposals: [],
      trace: [
        { role: 'planner', status: 'completed' },
        { role: 'researcher', status: 'completed' },
        { role: 'builder', status: 'completed' },
        { role: 'reviewer', status: 'completed' },
        { role: 'skill_learner', status: 'completed' },
      ],
    };
    api.runOrchestration.mockResolvedValueOnce(resultData);
    render(<OrchestratorPanel api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务描述'), { target: { value: '任务' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: 'D:/Bolt/Bolt' } });
    fireEvent.click(screen.getByText('运行编排'));
    await waitFor(() => expect(screen.getByText('编排结果')).toBeTruthy());
    expect(screen.getByText('构建摘要')).toBeTruthy();
  });

  it('shows approved verdict in green', async () => {
    const api = fakeApi();
    api.runOrchestration.mockResolvedValueOnce({ task_description: 't', rounds: 1, final_verdict: 'approved', builder_output: { summary: 's' }, review_findings: [], proposals: [], trace: [] });
    render(<OrchestratorPanel api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务描述'), { target: { value: '任务' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: 'D:/Bolt/Bolt' } });
    fireEvent.click(screen.getByText('运行编排'));
    await waitFor(() => expect(screen.getByText('approved')).toBeTruthy());
    const badge = screen.getByText('approved');
    expect(badge).toHaveStyle({ background: '#16a34a' });
  });

  it('shows blocked verdict in red', async () => {
    const api = fakeApi();
    api.runOrchestration.mockResolvedValueOnce({ task_description: 't', rounds: 1, final_verdict: 'blocked', builder_output: { summary: 's' }, review_findings: [], proposals: [], trace: [] });
    render(<OrchestratorPanel api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务描述'), { target: { value: '任务' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: 'D:/Bolt/Bolt' } });
    fireEvent.click(screen.getByText('运行编排'));
    await waitFor(() => expect(screen.getByText('blocked')).toBeTruthy());
    const badge = screen.getByText('blocked');
    expect(badge).toHaveStyle({ background: '#dc2626' });
  });

  it('shows proposals list', async () => {
    const api = fakeApi();
    api.runOrchestration.mockResolvedValueOnce({ task_description: 't', rounds: 1, final_verdict: 'approved', builder_output: { summary: 's' }, review_findings: [], proposals: [{ id: 'p1', title: '提案1' }], trace: [] });
    render(<OrchestratorPanel api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入任务描述'), { target: { value: '任务' } });
    fireEvent.change(screen.getByPlaceholderText('输入工作区路径'), { target: { value: 'D:/Bolt/Bolt' } });
    fireEvent.click(screen.getByText('运行编排'));
    await waitFor(() => expect(screen.getByText('提案')).toBeTruthy());
    expect(screen.getByText(/提案1/)).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<OrchestratorPanel api={fakeApi()} />);
    expect(screen.getByText('运行编排')).toBeTruthy();
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });
});
