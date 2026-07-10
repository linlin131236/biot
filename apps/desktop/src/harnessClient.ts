import type { AgentLoopResult, AgentStepResult, HarnessRun, MemoryConsolidationResult, MemoryQuery, MemoryRecord, MemorySnapshot, ModelSettings, ModelSettingsStatus, PendingPermission, ToolRequest, ToolResult, TraceEvent } from '@bolt/shared';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export async function createHarnessRun(goal: string, workspace: string, fetcher: Fetcher): Promise<HarnessRun> {
  return readJson(await fetcher('/harness/runs', jsonPost({ goal, workspace })));
}

export async function submitToolRequest(runId: string, request: ToolRequest, fetcher: Fetcher): Promise<ToolResult> {
  return readJson(await fetcher(`/harness/runs/${runId}/tool-requests`, jsonPost(request)));
}

export async function runAgentStep(runId: string, fetcher: Fetcher): Promise<AgentStepResult> {
  return readJson(await fetcher(`/harness/runs/${runId}/agent-steps`, { method: 'POST' }));
}

export async function runAgentLoop(runId: string, maxSteps: number, fetcher: Fetcher): Promise<AgentLoopResult> {
  return readJson(await fetcher(`/harness/runs/${runId}/agent-loops`, jsonPost({ max_steps: maxSteps })));
}

export async function fetchModelSettingsStatus(fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return readJson(await fetcher('/model/settings'));
}

export async function saveModelSettings(settings: ModelSettings, fetcher: Fetcher): Promise<ModelSettingsStatus> {
  return readJson(await fetcher('/model/settings', jsonPost(settings)));
}

export async function fetchHarnessTrace(runId: string, fetcher: Fetcher): Promise<TraceEvent[]> {
  return readJson(await fetcher(`/harness/runs/${runId}/trace`));
}

export async function fetchMemorySnapshot(fetcher: Fetcher): Promise<MemorySnapshot> {
  return readJson(await fetcher('/memory'));
}

export async function recordMemory(memory: Partial<MemoryRecord>, fetcher: Fetcher): Promise<MemoryRecord> {
  return readJson(await fetcher('/memory', jsonPost(memory)));
}

export async function fetchMemoryRecords(query: MemoryQuery = {}, fetcher: Fetcher): Promise<MemoryRecord[]> {
  const params = new URLSearchParams(query as Record<string, string>);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return readJson(await fetcher(`/memory/records${suffix}`));
}

export async function resolveMemory(memoryId: string, fetcher: Fetcher): Promise<MemoryRecord> {
  return readJson(await fetcher(`/memory/${memoryId}/resolve`, { method: 'POST' }));
}

export async function consolidateMemory(fetcher: Fetcher): Promise<MemoryConsolidationResult> {
  return readJson(await fetcher('/memory/consolidate', { method: 'POST' }));
}

export async function fetchPendingPermissions(fetcher: Fetcher): Promise<PendingPermission[]> {
  return readJson(await fetcher('/permissions/pending'));
}

export async function approvePermission(requestId: string, fetcher: Fetcher): Promise<ToolResult> {
  return readJson(await fetcher(`/permissions/${requestId}/approve`, { method: 'POST' }));
}

export async function rejectPermission(requestId: string, fetcher: Fetcher): Promise<ToolResult> {
  return readJson(await fetcher(`/permissions/${requestId}/reject`, { method: 'POST' }));
}

export async function runDocumentGardener(runId: string, fetcher: Fetcher): Promise<ToolResult> {
  return readJson(await fetcher(`/maintenance/document-gardener/runs/${runId}`, { method: 'POST' }));
}

export async function fetchDesktopSettings(fetcher: Fetcher): Promise<{
  theme: string;
  language: string;
  default_workspace: string;
  has_api_key: boolean;
  credential_revision: number;
}> {
  return readJson(await fetcher('/desktop/settings'));
}

export async function saveDesktopSettings(settings: { theme?: string; language?: string; default_workspace?: string }, fetcher: Fetcher): Promise<{ theme: string; language: string; default_workspace: string; has_api_key: boolean; credential_revision: number }> {
  return readJson(await fetcher('/desktop/settings', jsonPost(settings)));
}

export async function saveDesktopApiKey(apiKey: string, revision: number, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean; revision: number }> {
  return readJson(await fetcher('/desktop/settings/api-key', jsonPost({ api_key: apiKey, revision })));
}

export async function deleteDesktopApiKey(revision: number, fetcher: Fetcher): Promise<{ status: string; has_api_key: boolean; revision: number }> {
  return readJson(await fetcher(`/desktop/settings/api-key?revision=${revision}`, { method: 'DELETE' }));
}

export async function addWorkspaceHistory(path: string, fetcher: Fetcher): Promise<{ recent_workspaces: string[] }> {
  return readJson(await fetcher('/desktop/settings/workspace-history', jsonPost({ path })));
}

export async function fetchRecentSessions(limit: number = 20, fetcher: Fetcher): Promise<{ sessions: Array<{ id: string; title: string; time: string; status: string }> }> {
  const params = new URLSearchParams({ limit: String(limit) });
  return readJson(await fetcher(`/workspace/recent-sessions?${params}`));
}

export async function fetchWorkspaceStatus(fetcher: Fetcher): Promise<{ accessible: boolean; path: string }> {
  return readJson(await fetcher('/workspace/status'));
}

function jsonPost(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  return response.json() as Promise<T>;
}
