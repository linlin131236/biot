/** Autonomy protocol types: Goal, Conversation, Vector Memory, Skills,
 *  Delegation, Provider/MoA, Checkpoint/Review.
 *  Split from protocol.ts to respect the 300-line size gate.
 */

// === Goal Mode ===
export type GoalStatus = 'pending' | 'running' | 'paused' | 'stopped' | 'completed' | 'failed' | 'rejected';

export interface Goal {
  id: string;
  objective: string;
  criteria: string[];
  status: GoalStatus;
  max_steps: number;
  max_cost: number;
  max_wall_time: number;
  workspace: string;
  step_count: number;
}

// === Conversation ===
export interface ConversationMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_call_id?: string | null;
  tool_calls?: unknown[] | null;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// === Vector Memory ===
export interface MemoryVector {
  memory_id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

// === Skill System ===
export interface SkillManifest {
  name: string;
  triggers: string[];
  required_tools: string[];
  version: string;
  path: string;
  docs: string;
}

// === Delegation ===
export type AgentRole = 'planner' | 'researcher' | 'builder' | 'reviewer';
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'needs_revision';

export interface DelegationTask {
  id: string;
  role: AgentRole;
  objective: string;
  status: TaskStatus;
  inputs: Record<string, unknown>;
  constraints: string[];
  workspace: string;
  output: string;
  evidence: string[];
  reason: string;
}

// === Provider Policy & MoA ===
export type ProviderCapability = 'chat' | 'tool_calling' | 'vision' | 'embedding' | 'json_mode';

export interface ProviderPolicy {
  tier: string;
  max_cost_per_request: number;
  max_cost_per_day: number;
}

export interface MoAResult {
  selected: string | null;
  output: string;
  candidate_summaries: Array<{ model: string; summary: string }>;
  dissent?: string | null;
  reason: string;
  cost: number;
}

// === Checkpoint & Review ===
export interface Checkpoint {
  id: string;
  run_id: string;
  goal_id: string;
  changed_files: string[];
  file_contents?: Record<string, string> | null;
  constraints: string[];
  pending_permissions: string[];
  evidence_refs: string[];
}

export interface ReviewChecklist {
  items: string[];
}

export interface ReviewResult {
  passed: boolean;
  failures: string[];
}

// === Steering ===
export interface SteeringResult {
  status: string;
}

// === Goal Timeline & Evidence ===
export interface TimelineEvent {
  type: string;
  sequence: number;
  payload: Record<string, unknown>;
}

export interface GoalEvidence {
  phase: string;
  action: string;
  result: string;
  summary?: string;
  timestamp?: string;
}

// === Task Closure ===
export type TaskTemplateId = 'bugfix' | 'docs' | 'test' | 'quality' | 'review';

export interface TaskTemplate {
  id: TaskTemplateId;
  label: string;
  description: string;
  default_checks: string[];
}

export type TaskClosureStatus =
  | 'pending' | 'planning' | 'executing' | 'waiting_permission'
  | 'verifying' | 'repairing' | 'reviewing'
  | 'completed' | 'failed' | 'stopped';

export interface TaskClosureEvidence {
  id: string;
  objective: string;
  template_id: TaskTemplateId;
  run_id?: string | null;
  goal_id?: string | null;
  status: TaskClosureStatus;
  final_status: TaskClosureStatus;
  plan_summary: string;
  changed_files: string[];
  commands: string[];
  command_results: string[];
  permission_request_ids: string[];
  retry_count: number;
  review_summary: string;
  next_action: string;
  created_at?: number;
}

export type VerificationAssessmentStatus = 'passed' | 'failed' | 'missing_evidence' | 'waiting_permission' | 'needs_repair' | 'stopped';

export interface VerificationCheck {
  id: string;
  label: string;
  command?: string | null;
  required: boolean;
  satisfied: boolean;
  evidence: string;
  missing_reason: string;
}

export interface VerificationPlan {
  template_id: TaskTemplateId;
  checks: VerificationCheck[];
}

export interface VerificationAssessment {
  status: VerificationAssessmentStatus;
  summary: string;
  missing: string[];
  repair_suggestions: string[];
}

export type ExecutionQueueRisk = 'read_only' | 'verification_command' | 'workspace_write' | 'destructive';
export type ExecutionQueueStatus = 'pending' | 'approved' | 'rejected' | 'completed' | 'failed';
export type ExecutionQueueKind = 'verification_command' | 'repair_suggestion' | 'replan' | 'agent_loop' | 'manual_review';

export interface ExecutionQueueItem {
  id: string;
  closure_id: string;
  kind: ExecutionQueueKind;
  title: string;
  description: string;
  risk: ExecutionQueueRisk;
  status: ExecutionQueueStatus;
  command?: string | null;
  reason: string;
  result: string;
  created_at?: number;
}

export type ExecutionHandoffStatus = 'created' | 'ready_for_manual_action' | 'linked_to_goal' | 'waiting_permission' | 'completed' | 'failed';
export type ExecutionHandoffType = 'manual_verification' | 'permission_panel' | 'goal_input' | 'manual_review';
export type ExecutionHandoffPermissionStatus = 'not_requested' | 'pending_permission' | 'denied' | 'approved' | 'executed' | 'failed' | 'rejected';

export interface ExecutionHandoffRecord {
  id: string;
  queue_item_id: string;
  closure_id: string;
  kind: ExecutionQueueKind;
  status: ExecutionHandoffStatus;
  handoff_type: ExecutionHandoffType;
  title: string;
  instruction: string;
  command?: string | null;
  goal_objective: string;
  run_id?: string | null;
  goal_id?: string | null;
  permission_request_id?: string | null;
  permission_status: ExecutionHandoffPermissionStatus;
  bridge_error: string;
  created_at?: number;
  updated_at?: number;
  result: string;
}

export interface ExecutionAuditTimelineEvent {
  id: string;
  closure_id: string;
  source: 'queue' | 'handoff' | 'closure' | 'permission';
  status: string;
  label: string;
  summary: string;
  occurred_at: number;
  queue_item_id?: string | null;
  handoff_id?: string | null;
  permission_request_id?: string | null;
}

export const TASK_TEMPLATES: TaskTemplate[] = [
  { id: 'bugfix', label: '修复小问题', description: '定位并修复代码缺陷', default_checks: ['lint', 'test'] },
  { id: 'docs', label: '更新文档', description: '添加或修正文档内容', default_checks: ['lint:docs'] },
  { id: 'test', label: '增加测试', description: '为现有代码补充测试', default_checks: ['test', 'coverage'] },
  { id: 'quality', label: '跑质量门', description: '运行 lint/build/test 验证', default_checks: ['quality'] },
  { id: 'review', label: '生成审查摘要', description: '汇总变更和验证结果', default_checks: ['review'] },
];

export const TASK_CLOSURE_LABELS: Record<TaskClosureStatus, string> = {
  pending: '待开始',
  planning: '规划中',
  executing: '执行中',
  waiting_permission: '等待人工批准',
  verifying: '验证中',
  repairing: '修复中',
  reviewing: '审查中',
  completed: '已完成',
  failed: '已失败',
  stopped: '已停止',
};
