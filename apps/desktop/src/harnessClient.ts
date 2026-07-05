import type { AgentStepResult, HarnessRun, MemoryConsolidationResult, MemoryQuery, MemoryRecord, MemorySnapshot, ModelSettings, ModelSettingsStatus, PendingPermission, ToolRequest, ToolResult, TraceEvent } from '@bolt/shared';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export async function createHarnessRun(baseUrl: string, goal: string, fetcher: Fetcher = fetch): Promise<HarnessRun> {
  const response = await fetcher(`${baseUrl}/harness/runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ goal })
  });
  return response.json();
}

export async function submitToolRequest(
  baseUrl: string,
  runId: string,
  request: ToolRequest,
  fetcher: Fetcher = fetch
): Promise<ToolResult> {
  const response = await fetcher(`${baseUrl}/harness/runs/${runId}/tool-requests`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request)
  });
  return response.json();
}

export async function runAgentStep(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<AgentStepResult> {
  const response = await fetcher(`${baseUrl}/harness/runs/${runId}/agent-steps`, { method: 'POST' });
  return response.json();
}

export async function fetchModelSettingsStatus(baseUrl: string, fetcher: Fetcher = fetch): Promise<ModelSettingsStatus> {
  const response = await fetcher(`${baseUrl}/model/settings`);
  return response.json();
}

export async function saveModelSettings(baseUrl: string, settings: ModelSettings, fetcher: Fetcher = fetch): Promise<ModelSettingsStatus> {
  const response = await fetcher(`${baseUrl}/model/settings`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(settings)
  });
  return response.json();
}

export async function fetchHarnessTrace(
  baseUrl: string,
  runId: string,
  fetcher: Fetcher = fetch
): Promise<TraceEvent[]> {
  const response = await fetcher(`${baseUrl}/harness/runs/${runId}/trace`);
  return response.json();
}

export async function fetchMemorySnapshot(baseUrl: string, fetcher: Fetcher = fetch): Promise<MemorySnapshot> {
  const response = await fetcher(`${baseUrl}/memory`);
  return response.json();
}

export async function recordMemory(baseUrl: string, memory: Partial<MemoryRecord>, fetcher: Fetcher = fetch): Promise<MemoryRecord> {
  const response = await fetcher(`${baseUrl}/memory`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(memory)
  });
  return response.json();
}

export async function fetchMemoryRecords(baseUrl: string, query: MemoryQuery = {}, fetcher: Fetcher = fetch): Promise<MemoryRecord[]> {
  const params = new URLSearchParams(query as Record<string, string>);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await fetcher(`${baseUrl}/memory/records${suffix}`);
  return response.json();
}

export async function resolveMemory(baseUrl: string, memoryId: string, fetcher: Fetcher = fetch): Promise<MemoryRecord> {
  const response = await fetcher(`${baseUrl}/memory/${memoryId}/resolve`, { method: 'POST' });
  return response.json();
}

export async function consolidateMemory(baseUrl: string, fetcher: Fetcher = fetch): Promise<MemoryConsolidationResult> {
  const response = await fetcher(`${baseUrl}/memory/consolidate`, { method: 'POST' });
  return response.json();
}

export async function fetchPendingPermissions(baseUrl: string, fetcher: Fetcher = fetch): Promise<PendingPermission[]> {
  const response = await fetcher(`${baseUrl}/permissions/pending`);
  return response.json();
}

export async function approvePermission(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<ToolResult> {
  const response = await fetcher(`${baseUrl}/permissions/${requestId}/approve`, { method: 'POST' });
  return response.json();
}

export async function rejectPermission(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<ToolResult> {
  const response = await fetcher(`${baseUrl}/permissions/${requestId}/reject`, { method: 'POST' });
  return response.json();
}
