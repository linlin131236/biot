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

export async function startWorkflowRun(goal: string, workspace: string, fetcher: Fetcher): Promise<HarnessRun> {
  return createHarnessRun(goal, workspace, fetcher);
}

export async function executeWorkflowStep(runId: string, fetcher: Fetcher): Promise<{ step: AgentStepResult; refresh: WorkflowRefresh }> {
  const step = await runAgentStep(runId, fetcher);
  return { step, refresh: await refreshWorkflow(runId, fetcher) };
}

export async function refreshWorkflow(runId: string, fetcher: Fetcher): Promise<WorkflowRefresh> {
  const [trace, memory, permissions] = await Promise.all([
    fetchHarnessTrace(runId, fetcher),
    fetchMemorySnapshot(fetcher),
    fetchPendingPermissions(fetcher),
  ]);
  return { trace, memory, permissions };
}

export async function decidePermission(requestId: string, approved: boolean, fetcher: Fetcher): Promise<ToolResult> {
  return approved ? approvePermission(requestId, fetcher) : rejectPermission(requestId, fetcher);
}

export async function loadModelSettings(fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return fetchModelSettingsStatus(fetcher);
}

export async function storeModelSettings(settings: ModelSettings, fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return saveModelSettings(settings, fetcher);
}

export async function maintainMemory(runId: string, fetcher: Fetcher): Promise<ToolResult> {
  return runDocumentGardener(runId, fetcher);
}

export async function consolidateWorkflowMemory(fetcher: Fetcher): Promise<MemoryConsolidationResult> {
  return consolidateMemory(fetcher);
}

// === Dogfood path helpers ===

export async function createWorkflowGoal(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Goal> {
  return createGoal(payload, fetcher);
}

export async function createWorkflowConversation(payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ id: string }> {
  return createConversation(payload, fetcher);
}

export async function addWorkflowMessage(conversationId: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ status: string }> {
  return addMessage(conversationId, payload, fetcher);
}

export async function submitWorkflowTool(runId: string, request: { tool: string; operation: string; payload: Record<string, unknown> }, fetcher: Fetcher): Promise<ToolResult> {
  return submitToolRequest(runId, request, fetcher);
}

export async function createWorkflowCheckpoint(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Checkpoint> {
  return createCheckpoint(payload, fetcher);
}

export async function loadWorkflowCheckpoint(cpId: string, fetcher: Fetcher): Promise<Checkpoint | null> {
  return loadCheckpoint(cpId, fetcher);
}

export async function evaluateWorkflowReview(payload: { items: string[]; results: Record<string, boolean> }, fetcher: Fetcher): Promise<{ passed: boolean; failures: string[] }> {
  return evaluateReview(payload, fetcher);
}

export async function fetchWorkflowTimeline(runId: string, fetcher: Fetcher): Promise<unknown[]> {
  return fetchRunTimeline(runId, fetcher);
}

export async function loadDesktopSettings(fetcher: Fetcher): Promise<{ theme: string; language: string; default_workspace: string; has_api_key: boolean; credential_revision: number }> {
  return harnessFetchDesktopSettings(fetcher);
}

export async function storeDesktopSettings(settings: { theme?: string; language?: string; default_workspace?: string }, fetcher: Fetcher): Promise<{ theme: string; language: string; default_workspace: string; has_api_key: boolean; credential_revision: number }> {
  return harnessSaveDesktopSettings(settings, fetcher);
}

export async function storeDesktopApiKey(apiKey: string, revision: number, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean; revision: number }> {
  return harnessSaveDesktopApiKey(apiKey, revision, fetcher);
}

export async function removeDesktopApiKey(revision: number, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean; revision: number }> {
  return harnessDeleteDesktopApiKey(revision, fetcher);
}

export async function addWorkspaceToHistory(path: string, fetcher: Fetcher): Promise<void> {
  await harnessAddWorkspaceHistory(path, fetcher);
}

export async function loadRecentSessions(limit: number = 20, fetcher: Fetcher): Promise<Array<{ id: string; title: string; time: string; status: string }>> {
  const result = await harnessFetchRecentSessions(limit, fetcher);
  return result.sessions;
}

export async function loadWorkspaceStatus(fetcher: Fetcher): Promise<{ accessible: boolean; path: string }> {
  return harnessFetchWorkspaceStatus(fetcher);
}
