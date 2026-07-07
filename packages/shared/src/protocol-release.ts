/** Release readiness and checklist types. Split from protocol-autonomy.ts for size. */

export interface ReleaseReadinessCheck {
  code: string;
  label: string;
  passed: boolean;
  severity: 'blocking' | 'warning' | 'info';
  severity_label: '阻断' | '警告' | '提示';
  detail: string;
}

export interface ReleaseReadiness {
  ready: boolean;
  checks: ReleaseReadinessCheck[];
  blockers: string[];
  warnings: string[];
}

export interface LocalReleaseChecklistItem {
  code: string;
  category: string;
  label: string;
  status: 'pass' | 'fail' | 'warn';
  status_label: string;
  detail: string;
  recommendation: string | null;
}

export interface LocalReleaseChecklist {
  ready: boolean;
  items: LocalReleaseChecklistItem[];
  blockers: string[];
  warnings: string[];
  next_step: string;
  disclaimer: string;
}

export interface RecoveryScenario {
  code: string;
  title: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  severity_label: string;
  description: string;
  recovery_steps: string[];
  auto_recovery_possible: boolean;
  auto_recovery_label: string;
  warnings: string[];
}

export interface RecoveryPolicy {
  scenarios: RecoveryScenario[];
  categories: Record<string, RecoveryScenario[]>;
  total: number;
  disclaimer: string;
}

// === Planner Task Graph (M61) ===

export type TaskNodeStatus = 'pending' | 'in_progress' | 'blocked' | 'completed' | 'failed';
export type TaskNodeRisk = 'low' | 'medium' | 'high' | 'critical';
export type TaskNodeRole = 'planner' | 'builder' | 'reviewer' | 'researcher';

export interface TaskNode {
  id: string;
  title: string;
  status: TaskNodeStatus;
  dependencies: string[];
  risk: TaskNodeRisk;
  owner_role: TaskNodeRole;
  evidence_refs: string[];
  created_at: number;
  updated_at: number;
}

export interface TaskGraph {
  id: string;
  title: string;
  objective: string;
  nodes: TaskNode[];
  created_at: number;
  updated_at: number;
}

export interface TaskGraphSummary {
  id: string;
  title: string;
  objective: string;
  node_count: number;
  created_at: number;
  updated_at: number;
}

// === Execution State Machine (M62) ===

export type ExecState = 'pending' | 'ready' | 'running' | 'waiting_permission' | 'paused' | 'completed' | 'failed' | 'blocked';

export interface StateMachineSummary {
  states: Record<string, string>;
  terminal: string[];
  transitions: Record<string, string[]>;
}

export interface AllowedTransitions {
  from_state: string;
  from_label: string;
  allowed: string[];
  allowed_labels: string[];
  is_terminal: boolean;
}

export interface TransitionResult {
  node_id: string;
  from_state: string;
  to_state: string;
  from_label: string;
  to_label: string;
  reason: string;
  valid: boolean;
}

// === Tool Selection Policy (M63) ===

export interface ToolClassSummary {
  classes: Record<string, string>;
  counts: Record<string, number>;
  total: number;
}

export interface ToolInfo {
  name: string;
  class: string;
  label: string;
  description: string;
}

export interface ToolSelectionResultItem {
  tool: string;
  class: string;
  label: string;
  allowed: boolean;
  requires_permission: boolean;
  warnings: string[];
  suggestion: string;
}

export interface ToolSelectionResult {
  results: ToolSelectionResultItem[];
  all_allowed: boolean;
  any_requires_permission: boolean;
  reason: string;
  disclaimer: string;
}
