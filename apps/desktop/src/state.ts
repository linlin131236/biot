import type { AgentStepResult, MemoryConsolidationResult, MemorySnapshot, ModelSettingsStatus, PendingPermission, ToolResult } from '@bolt/shared';

export type CoreStatus = 'unknown' | 'ok' | 'down';
export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  role: MessageRole;
  content: string;
}

export interface TraceEvent {
  run_id: string;
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
}

export interface BoltState {
  workspacePath: string | null;
  coreStatus: CoreStatus;
  messages: ChatMessage[];
  currentRunId: string | null;
  traceEvents: TraceEvent[];
  memorySnapshot: MemorySnapshot | null;
  pendingPermissions: PendingPermission[];
  toolResults: ToolResult[];
  modelSettingsStatus: ModelSettingsStatus | null;
  agentStepResults: AgentStepResult[];
  memoryConsolidationResult: MemoryConsolidationResult | null;
}

export type BoltAction =
  | { type: 'workspace.selected'; path: string }
  | { type: 'core.health.changed'; status: CoreStatus }
  | { type: 'chat.message.added'; role: MessageRole; content: string }
  | { type: 'harness.run.created'; runId: string }
  | { type: 'harness.trace.loaded'; events: TraceEvent[] }
  | { type: 'memory.snapshot.loaded'; snapshot: MemorySnapshot }
  | { type: 'permissions.pending.loaded'; permissions: PendingPermission[] }
  | { type: 'model.settings.loaded'; status: ModelSettingsStatus }
  | { type: 'memory.consolidation.recorded'; result: MemoryConsolidationResult }
  | { type: 'agent.step.recorded'; result: AgentStepResult }
  | { type: 'tool.result.recorded'; result: ToolResult };

export function createBoltState(): BoltState {
  return { workspacePath: null, coreStatus: 'unknown', messages: [], currentRunId: null, traceEvents: [], memorySnapshot: null, pendingPermissions: [], toolResults: [], modelSettingsStatus: null, agentStepResults: [], memoryConsolidationResult: null };
}

export function reduceBoltState(state: BoltState, action: BoltAction): BoltState {
  if (action.type === 'harness.run.created') return { ...state, currentRunId: action.runId };
  if (action.type === 'harness.trace.loaded') return { ...state, traceEvents: action.events };
  if (action.type === 'memory.snapshot.loaded') return { ...state, memorySnapshot: action.snapshot };
  if (action.type === 'permissions.pending.loaded') return { ...state, pendingPermissions: action.permissions };
  if (action.type === 'model.settings.loaded') return { ...state, modelSettingsStatus: action.status };
  if (action.type === 'memory.consolidation.recorded') return { ...state, memoryConsolidationResult: action.result };
  if (action.type === 'agent.step.recorded') return { ...state, agentStepResults: [...state.agentStepResults, action.result] };
  if (action.type === 'tool.result.recorded') return { ...state, toolResults: [...state.toolResults, action.result] };
  if (action.type === 'workspace.selected') return { ...state, workspacePath: action.path };
  if (action.type === 'core.health.changed') return { ...state, coreStatus: action.status };
  return { ...state, messages: [...state.messages, toMessage(action)] };
}

function toMessage(action: Extract<BoltAction, { type: 'chat.message.added' }>): ChatMessage {
  return { role: action.role, content: action.content };
}
