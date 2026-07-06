import { describe, expect, it } from 'vitest';
import type { Goal, GoalStatus, TimelineEvent, GoalEvidence, ReviewResult, Checkpoint, SteeringResult, VerificationAssessmentStatus, ExecutionQueueKind, ExecutionQueueRisk, ExecutionQueueStatus, ExecutionHandoffStatus, ExecutionHandoffType, ExecutionAuditTimelineEvent } from './protocol-autonomy';

describe('shared autonomy protocol', () => {
  it('supports Goal shape', () => {
    const goal: Goal = {
      id: 'goal_abc12345',
      objective: '修复 README',
      criteria: ['拼写已修正'],
      status: 'paused',
      max_steps: 10,
      max_cost: 5.0,
      max_wall_time: 300,
      workspace: 'D:/Projects/Bolt',
      step_count: 3,
    };
    expect(goal.status).toBe('paused');
    expect(goal.step_count).toBe(3);
  });

  it('covers all GoalStatus values', () => {
    const statuses: GoalStatus[] = ['pending', 'running', 'paused', 'stopped', 'completed', 'failed', 'rejected'];
    expect(statuses).toHaveLength(7);
  });

  it('supports TimelineEvent shape', () => {
    const event: TimelineEvent = { type: 'run.created', sequence: 1, payload: {} };
    expect(event.type).toBe('run.created');
    expect(event.sequence).toBe(1);
  });

  it('supports GoalEvidence shape', () => {
    const evidence: GoalEvidence = { phase: 'test', action: 'pytest', result: 'pass', summary: '299 ok' };
    expect(evidence.phase).toBe('test');
    expect(evidence.summary).toBe('299 ok');
  });

  it('supports Checkpoint shape', () => {
    const cp: Checkpoint = {
      id: 'cp_1234abcd',
      run_id: 'run_1',
      goal_id: 'goal_1',
      changed_files: ['main.py'],
      constraints: [],
      pending_permissions: [],
      evidence_refs: [],
    };
    expect(cp.changed_files).toHaveLength(1);
  });

  it('supports ReviewResult shape', () => {
    const result: ReviewResult = { passed: false, failures: ['lint'] };
    expect(result.passed).toBe(false);
    expect(result.failures).toContain('lint');
  });

  it('supports SteeringResult shape', () => {
    const s: SteeringResult = { status: 'injected' };
    expect(s.status).toBe('injected');
  });

  it('supports TaskTemplate and TASK_TEMPLATES', async () => {
    const { TASK_TEMPLATES, TASK_CLOSURE_LABELS } = await import('./protocol-autonomy');
    expect(TASK_TEMPLATES).toHaveLength(5);
    expect(TASK_TEMPLATES[0].id).toBe('bugfix');
    expect(TASK_TEMPLATES[0].label).toBe('修复小问题');
    expect(TASK_TEMPLATES[1].id).toBe('docs');
    expect(TASK_TEMPLATES[2].id).toBe('test');
    expect(TASK_TEMPLATES[3].id).toBe('quality');
    expect(TASK_TEMPLATES[4].id).toBe('review');
  });

  it('covers all TaskClosureStatus values with Chinese labels', async () => {
    const { TASK_CLOSURE_LABELS } = await import('./protocol-autonomy');
    const statuses = Object.keys(TASK_CLOSURE_LABELS);
    expect(statuses).toHaveLength(10);
    expect(TASK_CLOSURE_LABELS.pending).toBe('待开始');
    expect(TASK_CLOSURE_LABELS.completed).toBe('已完成');
    expect(TASK_CLOSURE_LABELS.failed).toBe('已失败');
    expect(TASK_CLOSURE_LABELS.waiting_permission).toBe('等待人工批准');
  });

  it('supports TaskClosureEvidence shape', async () => {
    const type = await import('./protocol-autonomy');
    const evidence: type.TaskClosureEvidence = {
      id: 'cl_43',
      objective: '修复拼写错误',
      template_id: 'bugfix',
      run_id: 'run_43',
      goal_id: 'goal_43',
      status: 'completed',
      final_status: 'completed',
      plan_summary: '读取文件→修改→验证',
      changed_files: ['README.md'],
      commands: ['pnpm test'],
      command_results: ['pass'],
      permission_request_ids: [],
      retry_count: 0,
      review_summary: '所有测试通过',
      next_action: '无',
    };
    expect(evidence.template_id).toBe('bugfix');
    expect(evidence.retry_count).toBe(0);
    expect(evidence.final_status).toBe('completed');
  });

  it('supports verification plan with Chinese check labels', async () => {
    const type = await import('./protocol-autonomy');
    const plan: type.VerificationPlan = {
      template_id: 'bugfix',
      checks: [{ id: 'quality', label: '测试或质量门证据', command: 'pytest', required: true, satisfied: false, evidence: '', missing_reason: '缺少测试证据' }],
    };
    expect(plan.checks[0].label).toBe('测试或质量门证据');
  });

  it('covers all verification assessment statuses', () => {
    const statuses: VerificationAssessmentStatus[] = ['passed', 'failed', 'missing_evidence', 'waiting_permission', 'needs_repair', 'stopped'];
    expect(statuses).toHaveLength(6);
  });

  it('supports execution queue item and covers enums', async () => {
    const type = await import('./protocol-autonomy');
    const kinds: ExecutionQueueKind[] = ['verification_command', 'repair_suggestion', 'replan', 'agent_loop', 'manual_review'];
    const risks: ExecutionQueueRisk[] = ['read_only', 'verification_command', 'workspace_write', 'destructive'];
    const statuses: ExecutionQueueStatus[] = ['pending', 'approved', 'rejected', 'completed', 'failed'];
    const item: type.ExecutionQueueItem = {
      id: 'eq_1',
      closure_id: 'cl_1',
      kind: 'verification_command',
      title: '记录验证命令',
      description: '缺少测试证据',
      risk: 'verification_command',
      status: 'pending',
      command: 'pytest',
      reason: '',
      result: '',
    };

    expect(kinds).toHaveLength(5);
    expect(risks).toHaveLength(4);
    expect(statuses).toHaveLength(5);
    expect(item.title).toBe('记录验证命令');
  });

  it('supports execution handoff record and covers enums', async () => {
    const type = await import('./protocol-autonomy');
    const statuses: ExecutionHandoffStatus[] = ['created', 'ready_for_manual_action', 'linked_to_goal', 'waiting_permission', 'completed', 'failed'];
    const handoffTypes: ExecutionHandoffType[] = ['manual_verification', 'permission_panel', 'goal_input', 'manual_review'];
    const record: type.ExecutionHandoffRecord = {
      id: 'eh_1',
      queue_item_id: 'eq_1',
      closure_id: 'cl_1',
      kind: 'verification_command',
      status: 'ready_for_manual_action',
      handoff_type: 'manual_verification',
      title: '记录验证命令',
      instruction: '请在外部终端人工运行',
      command: 'pytest',
      goal_objective: '',
      run_id: null,
      goal_id: null,
      permission_request_id: null,
      permission_status: 'not_requested',
      bridge_error: '',
      result: '',
    };

    expect(statuses).toHaveLength(6);
    expect(handoffTypes).toHaveLength(4);
    expect(record.handoff_type).toBe('manual_verification');
    expect(record.permission_status).toBe('not_requested');
  });

  it('supports execution audit timeline event shape', () => {
    const event: ExecutionAuditTimelineEvent = {
      id: 'audit_1',
      closure_id: 'cl_1',
      source: 'permission',
      status: 'executed',
      label: '已执行',
      summary: '权限执行已返回结果',
      occurred_at: 10,
      queue_item_id: 'eq_1',
      handoff_id: 'eh_1',
      permission_request_id: 'tool_1',
    };

    expect(event.label).toBe('已执行');
    expect(event.permission_request_id).toBe('tool_1');
  });
});
