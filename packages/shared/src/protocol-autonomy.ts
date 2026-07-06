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
