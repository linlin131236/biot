import type { AgentStepResult, HarnessRun, MemoryConsolidationResult, MemorySnapshot, ModelSettings, ModelSettingsStatus, PendingPermission, ToolResult, TraceEvent } from '@bolt/shared';
import { approvePermission, consolidateMemory, createHarnessRun, fetchHarnessTrace, fetchMemorySnapshot, fetchModelSettingsStatus, fetchPendingPermissions, rejectPermission, runAgentStep, runDocumentGardener, saveModelSettings } from './harnessClient';

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
    fetchPendingPermissions(baseUrl, fetcher)
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
