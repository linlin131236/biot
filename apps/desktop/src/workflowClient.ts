import type { AgentStepResult, HarnessRun, MemoryConsolidationResult, MemorySnapshot, ModelSettings, ModelSettingsStatus, PendingPermission, ToolResult, TraceEvent } from '@bolt/shared';
import type { Goal, Checkpoint } from '@bolt/shared/autonomy';
import { approvePermission, consolidateMemory, createHarnessRun, fetchHarnessTrace, fetchMemorySnapshot, fetchModelSettingsStatus, fetchPendingPermissions, rejectPermission, runAgentStep, runDocumentGardener, saveModelSettings, saveDesktopSettings as harnessSaveDesktopSettings, fetchDesktopSettings as harnessFetchDesktopSettings, saveDesktopApiKey as harnessSaveDesktopApiKey, deleteDesktopApiKey as harnessDeleteDesktopApiKey, addWorkspaceHistory as harnessAddWorkspaceHistory, fetchRecentSessions as harnessFetchRecentSessions, fetchWorkspaceStatus as harnessFetchWorkspaceStatus, submitToolRequest } from './harnessClient';
import { createGoal, createCheckpoint, loadCheckpoint, evaluateReview, fetchRunTimeline, createConversation, addMessage } from './harnessClientAutonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface WorkflowRefresh {
  trace?: TraceEvent[];
  memory?: MemorySnapshot;
  permissions?: PendingPermission[];
}

export async function startWorkflowRun(baseUrl: string, goal: string, workspace: string, fetcher: Fetcher): Promise<HarnessRun> {
  return createHarnessRun(baseUrl, goal, workspace, fetcher);
}

export async function executeWorkflowStep(baseUrl: string, runId: string, fetcher: Fetcher): Promise<{ step: AgentStepResult; refresh: WorkflowRefresh }> {
  const step = await runAgentStep(baseUrl, runId, fetcher);
  return { step, refresh: await refreshWorkflow(baseUrl, runId, fetcher) };
}

export async function refreshWorkflow(baseUrl: string, runId: string, fetcher: Fetcher): Promise<WorkflowRefresh> {
  const [trace, memory, permissions] = await Promise.all([
    fetchHarnessTrace(baseUrl, runId, fetcher),
    fetchMemorySnapshot(baseUrl, fetcher),
    fetchPendingPermissions(baseUrl, fetcher),
  ]);
  return { trace, memory, permissions };
}

export async function decidePermission(baseUrl: string, requestId: string, approved: boolean, fetcher: Fetcher): Promise<ToolResult> {
  return approved ? approvePermission(baseUrl, requestId, fetcher) : rejectPermission(baseUrl, requestId, fetcher);
}

export async function loadModelSettings(baseUrl: string, fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return fetchModelSettingsStatus(baseUrl, fetcher);
}

export async function storeModelSettings(baseUrl: string, settings: ModelSettings, fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return saveModelSettings(baseUrl, settings, fetcher);
}

export async function maintainMemory(baseUrl: string, runId: string, fetcher: Fetcher): Promise<ToolResult> {
  return runDocumentGardener(baseUrl, runId, fetcher);
}

export async function consolidateWorkflowMemory(baseUrl: string, fetcher: Fetcher): Promise<MemoryConsolidationResult> {
  return consolidateMemory(baseUrl, fetcher);
}

// === Dogfood path helpers ===

export async function createWorkflowGoal(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<Goal> {
  return createGoal(baseUrl, payload, fetcher);
}

export async function createWorkflowConversation(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ id: string }> {
  return createConversation(baseUrl, payload, fetcher);
}

export async function addWorkflowMessage(baseUrl: string, conversationId: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ status: string }> {
  return addMessage(baseUrl, conversationId, payload, fetcher);
}

export async function submitWorkflowTool(baseUrl: string, runId: string, request: { tool: string; operation: string; payload: Record<string, unknown> }, fetcher: Fetcher): Promise<ToolResult> {
  return submitToolRequest(baseUrl, runId, request, fetcher);
}

export async function createWorkflowCheckpoint(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<Checkpoint> {
  return createCheckpoint(baseUrl, payload, fetcher);
}

export async function loadWorkflowCheckpoint(baseUrl: string, cpId: string, fetcher: Fetcher): Promise<Checkpoint | null> {
  return loadCheckpoint(baseUrl, cpId, fetcher);
}

export async function evaluateWorkflowReview(baseUrl: string, payload: { items: string[]; results: Record<string, boolean> }, fetcher: Fetcher): Promise<{ passed: boolean; failures: string[] }> {
  return evaluateReview(baseUrl, payload, fetcher);
}

export async function fetchWorkflowTimeline(baseUrl: string, runId: string, fetcher: Fetcher): Promise<unknown[]> {
  return fetchRunTimeline(baseUrl, runId, fetcher);
}

export async function loadDesktopSettings(baseUrl: string, fetcher: Fetcher): Promise<{ theme: string; language: string; default_workspace: string; has_api_key: boolean }> {
  return harnessFetchDesktopSettings(baseUrl, fetcher);
}

export async function storeDesktopSettings(baseUrl: string, settings: { theme?: string; language?: string; default_workspace?: string }, fetcher: Fetcher): Promise<{ theme: string; language: string; default_workspace: string; has_api_key: boolean }> {
  return harnessSaveDesktopSettings(baseUrl, settings, fetcher);
}

export async function storeDesktopApiKey(baseUrl: string, apiKey: string, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean }> {
  return harnessSaveDesktopApiKey(baseUrl, apiKey, fetcher);
}

export async function removeDesktopApiKey(baseUrl: string, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean }> {
  return harnessDeleteDesktopApiKey(baseUrl, fetcher);
}

export async function addWorkspaceToHistory(baseUrl: string, path: string, fetcher: Fetcher): Promise<void> {
  await harnessAddWorkspaceHistory(baseUrl, path, fetcher);
}

export async function loadRecentSessions(baseUrl: string, limit: number = 20, fetcher: Fetcher): Promise<Array<{ id: string; title: string; time: string; status: string }>> {
  const result = await harnessFetchRecentSessions(baseUrl, limit, fetcher);
  return result.sessions;
}

export async function loadWorkspaceStatus(baseUrl: string, fetcher: Fetcher): Promise<{ accessible: boolean; path: string }> {
  return harnessFetchWorkspaceStatus(baseUrl, fetcher);
}
