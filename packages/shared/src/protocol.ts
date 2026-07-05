export type ToolStatus = 'allowed' | 'pending_permission' | 'approved' | 'rejected' | 'denied' | 'executed' | 'failed';
export type PermissionStatus = 'pending_permission' | 'approved' | 'rejected' | 'denied';
export type MemoryKind = 'session' | 'project' | 'user' | 'tool' | 'failure' | 'long_term';
export type MemoryStatus = 'active' | 'resolved';

export interface HarnessRun {
  id: string;
  goal: string;
  workspace: string;
}

export interface ChangeSet {
  path: string;
  base_hash: string;
  proposed: string;
  diff: string;
  status: string;
}

export interface ShellCommandPayload {
  command: string;
  workdir: string;
  timeout_seconds?: number;
}

export interface ModelSettings {
  provider: string;
  base_url: string;
  model: string;
  temperature: number;
  api_key?: string;
}

export interface ModelSettingsStatus {
  provider: string;
  base_url: string;
  model: string;
  temperature: number;
  has_api_key: boolean;
}

export interface AgentStepResult {
  status: ToolStatus;
  model_output: string;
  tool_result?: ToolResult | null;
  error?: string | null;
}

export interface AgentLoopResult {
  status: ToolStatus;
  steps: number;
  last_step?: AgentStepResult | null;
  error?: string | null;
}

export interface ContextPacket {
  goal: string;
  p0_context: P0Context;
  recent_trace: TraceEvent[];
  token_budget: number;
  memory_context: Array<Record<string, unknown>>;
}

export interface ToolRequest {
  tool: string;
  operation: string;
  payload: Record<string, unknown>;
}

export interface ToolResult {
  request_id: string;
  status: ToolStatus;
  reason: string;
  output?: string | null;
  error?: string | null;
}

export interface PendingPermission {
  id: string;
  run_id: string;
  request_id: string;
  tool: string;
  operation: string;
  payload: Record<string, unknown>;
  action: string;
  reason: string;
  status: PermissionStatus;
}

export interface TraceEvent {
  run_id: string;
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
}

export interface P0Context {
  unresolved_failures: Array<Record<string, string>>;
  hard_constraints: string[];
}

export interface MemoryRecord {
  id: string;
  kind: MemoryKind;
  scope: string;
  content: string;
  status: MemoryStatus;
  source: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface MemoryQuery {
  kind?: MemoryKind;
  scope?: string;
  status?: MemoryStatus;
  query?: string;
}

export interface MemoryConsolidationResult {
  created: number;
  sources: number;
}

export interface WorkspaceProfile {
  root_path: string;
  name: string;
  package_manager?: string | null;
  languages: string[];
  manifests: string[];
  entry_files: string[];
  test_commands: string[];
  build_commands: string[];
  skipped: Record<string, number>;
  truncated: boolean;
}

export interface FileIndexEntry {
  path: string;
  imports: string[];
  exports: string[];
  symbols: string[];
}

export interface FileIndex {
  entries: FileIndexEntry[];
  skipped: Record<string, number>;
  truncated: boolean;
}

export interface IntentClassification {
  category: string;
  confidence: number;
  signals: string[];
}

export interface RuntimeObservation {
  status: string;
  ports: number[];
  processes: string[];
}

export interface UiObservation {
  status: string;
  workspace_path: string;
  current_file?: string | null;
  selection?: string | null;
}

export interface SchedulerDecision {
  priority: string;
  task: string;
  status: string;
}

export interface PerceptionSnapshot {
  workspace_profile: WorkspaceProfile;
  file_index: FileIndex;
  intent: IntentClassification;
  runtime: RuntimeObservation;
  ui: UiObservation;
  scheduler: SchedulerDecision[];
}

export interface MemorySnapshot {
  records: MemoryRecord[];
  p0_context: P0Context;
  workspace_profile?: WorkspaceProfile;
  perception_snapshot?: PerceptionSnapshot;
}

export function isHarnessRun(value: unknown): value is HarnessRun {
  if (!isRecord(value)) return false;
  return typeof value.id === 'string' && typeof value.goal === 'string' && typeof value.workspace === 'string';
}

export function isToolRequest(value: unknown): value is ToolRequest {
  if (!isRecord(value)) return false;
  return typeof value.tool === 'string' && typeof value.operation === 'string' && isRecord(value.payload);
}

export function isMemorySnapshot(value: unknown): value is MemorySnapshot {
  if (!isRecord(value)) return false;
  return Array.isArray(value.records) && isRecord(value.p0_context);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
