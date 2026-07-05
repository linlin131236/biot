import type { AgentLoopResult, AgentStepResult, HarnessRun, MemoryConsolidationResult, MemoryQuery, MemoryRecord, MemorySnapshot, ModelSettings, ModelSettingsStatus, PendingPermission, ToolRequest, ToolResult, TraceEvent } from '@bolt/shared';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export async function createHarnessRun(baseUrl: string, goal: string, workspace: string, fetcher: Fetcher = fetch): Promise<HarnessRun> {
  return readJson(await fetcher(`${baseUrl}/harness/runs`, jsonPost({ goal, workspace })));
}

export async function submitToolRequest(baseUrl: string, runId: string, request: ToolRequest, fetcher: Fetcher = fetch): Promise<ToolResult> {
  return readJson(await fetcher(`${baseUrl}/harness/runs/${runId}/tool-requests`, jsonPost(request)));
}

export async function runAgentStep(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<AgentStepResult> {
  return readJson(await fetcher(`${baseUrl}/harness/runs/${runId}/agent-steps`, { method: 'POST' }));
}

export async function runAgentLoop(baseUrl: string, runId: string, maxSteps: number, fetcher: Fetcher = fetch): Promise<AgentLoopResult> {
  return readJson(await fetcher(`${baseUrl}/harness/runs/${runId}/agent-loops`, jsonPost({ max_steps: maxSteps })));
}

export async function fetchModelSettingsStatus(baseUrl: string, fetcher: Fetcher = fetch): Promise<ModelSettingsStatus> {
  return readJson(await fetcher(`${baseUrl}/model/settings`));
}

export async function saveModelSettings(baseUrl: string, settings: ModelSettings, fetcher: Fetcher = fetch): Promise<ModelSettingsStatus> {
  return readJson(await fetcher(`${baseUrl}/model/settings`, jsonPost(settings)));
}

export async function fetchHarnessTrace(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<TraceEvent[]> {
  return readJson(await fetcher(`${baseUrl}/harness/runs/${runId}/trace`));
}

export async function fetchMemorySnapshot(baseUrl: string, fetcher: Fetcher = fetch): Promise<MemorySnapshot> {
  return readJson(await fetcher(`${baseUrl}/memory`));
}

export async function recordMemory(baseUrl: string, memory: Partial<MemoryRecord>, fetcher: Fetcher = fetch): Promise<MemoryRecord> {
  return readJson(await fetcher(`${baseUrl}/memory`, jsonPost(memory)));
}

export async function fetchMemoryRecords(baseUrl: string, query: MemoryQuery = {}, fetcher: Fetcher = fetch): Promise<MemoryRecord[]> {
  const params = new URLSearchParams(query as Record<string, string>);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return readJson(await fetcher(`${baseUrl}/memory/records${suffix}`));
}

export async function resolveMemory(baseUrl: string, memoryId: string, fetcher: Fetcher = fetch): Promise<MemoryRecord> {
  return readJson(await fetcher(`${baseUrl}/memory/${memoryId}/resolve`, { method: 'POST' }));
}

export async function consolidateMemory(baseUrl: string, fetcher: Fetcher = fetch): Promise<MemoryConsolidationResult> {
  return readJson(await fetcher(`${baseUrl}/memory/consolidate`, { method: 'POST' }));
}

export async function fetchPendingPermissions(baseUrl: string, fetcher: Fetcher = fetch): Promise<PendingPermission[]> {
  return readJson(await fetcher(`${baseUrl}/permissions/pending`));
}

export async function approvePermission(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<ToolResult> {
  return readJson(await fetcher(`${baseUrl}/permissions/${requestId}/approve`, { method: 'POST' }));
}

export async function rejectPermission(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<ToolResult> {
  return readJson(await fetcher(`${baseUrl}/permissions/${requestId}/reject`, { method: 'POST' }));
}

export async function runDocumentGardener(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<ToolResult> {
  return readJson(await fetcher(`${baseUrl}/maintenance/document-gardener/runs/${runId}`, { method: 'POST' }));
}

function jsonPost(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  return response.json() as Promise<T>;
}
