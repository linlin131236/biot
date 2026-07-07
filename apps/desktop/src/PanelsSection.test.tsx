import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PanelsSection } from './PanelsSection';
import type { TaskClosureEvidence } from '@bolt/shared/autonomy';

vi.mock('./CheckpointPanel', () => ({ CheckpointPanel: () => <aside>检查点</aside> }));
vi.mock('./GoalConsole', () => ({ GoalConsole: () => <aside>目标控制台</aside> }));
vi.mock('./SideChatPanel', () => ({ SideChatPanel: () => <aside>侧边对话</aside> }));
vi.mock('./TaskClosurePanel', () => ({ default: ({ onClosureChange }: { onClosureChange?: (id: string | null) => void }) => <aside><button type="button" onClick={() => onClosureChange?.('cl_a')}>切换闭环A</button><button type="button" onClick={() => onClosureChange?.('cl_b')}>切换闭环B</button></aside> }));

const closure: TaskClosureEvidence = {
  id: 'cl_a',
  objective: '修复问题',
  template_id: 'bugfix',
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
};

function apiFixture() {
  return {
    checkpoint: { createCheckpoint: vi.fn(), loadCheckpoint: vi.fn() },
    goal: { createGoal: vi.fn(), startRun: vi.fn(), runAgentLoop: vi.fn(), pauseGoal: vi.fn(), resumeGoal: vi.fn(), clearGoal: vi.fn(), getGoal: vi.fn(), fetchGoalEvidence: vi.fn(), fetchRunTimeline: vi.fn() },
    sideChat: { steerRun: vi.fn() },
    taskClosure: { fetchTaskTemplates: vi.fn(), createTaskClosure: vi.fn().mockResolvedValue(closure), getTaskClosure: vi.fn().mockResolvedValue(closure), addClosureEvent: vi.fn(), addClosureReview: vi.fn(), bindTaskClosureRun: vi.fn(), bindTaskClosureGoal: vi.fn(), fetchTaskClosureVerificationPlan: vi.fn(), fetchTaskClosureAssessment: vi.fn(), updateTaskClosureAssessment: vi.fn() },
    executionQueue: { fetchExecutionQueue: vi.fn().mockImplementation((_baseUrl: string, closureId?: string) => Promise.resolve(closureId === 'cl_a' ? [{ id: 'eq_a', closure_id: 'cl_a', kind: 'verification_command', title: '记录验证命令', description: '缺少测试', risk: 'verification_command', status: 'approved', command: 'pytest', reason: '', result: '' }] : [])), proposeExecutionQueue: vi.fn().mockResolvedValue([]), approveExecutionQueueItem: vi.fn(), rejectExecutionQueueItem: vi.fn(), completeExecutionQueueItem: vi.fn(), failExecutionQueueItem: vi.fn() },
    executionHandoff: { fetchExecutionHandoffs: vi.fn().mockResolvedValue([]), fetchExecutionAuditTimeline: vi.fn().mockResolvedValue([]), fetchExecutionAuditDiagnostics: vi.fn().mockResolvedValue([]), fetchExecutionAuditIntegrity: vi.fn().mockResolvedValue([]), fetchReleaseReadiness: vi.fn().mockResolvedValue({ ready: true, checks: [], blockers: [], warnings: [] }), fetchLocalReleaseChecklist: vi.fn().mockResolvedValue({ ready: true, items: [], blockers: [], warnings: [], next_step: '', disclaimer: '' }), fetchRecoveryPolicy: vi.fn().mockResolvedValue({ scenarios: [], categories: {}, total: 0, disclaimer: '' }), fetchPlannerGraphs: vi.fn().mockResolvedValue([]), createExecutionHandoff: vi.fn(), completeExecutionHandoff: vi.fn(), failExecutionHandoff: vi.fn(), requestExecutionHandoffPermission: vi.fn() },
  };
}

describe('PanelsSection', () => {
  it('切换闭环时清空已批准队列项，避免旧队列项生成交接', async () => {
    const api = apiFixture();
    render(<PanelsSection runId={null} goalInfo={null} unfinishedGoals={[]} workspace="D:/Bolt/Bolt" baseUrl="http://core" onGoalChange={vi.fn()} api={api} />);

    fireEvent.click(screen.getByRole('button', { name: '切换闭环A' }));
    fireEvent.click(await screen.findByRole('button', { name: '用于交接' }));
    fireEvent.click(screen.getByRole('button', { name: '切换闭环B' }));
    fireEvent.click(await screen.findByRole('button', { name: '生成安全交接' }));

    expect(await screen.findByText('请先选择已批准队列项')).toBeInTheDocument();
    expect(api.executionHandoff.createExecutionHandoff).not.toHaveBeenCalled();
  });
});
