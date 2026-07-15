export type RuntimeCapabilities = {
  messages: boolean;
  planning: boolean;
  tools: boolean;
  file_changes: boolean;
  shell: boolean;
  permissions: boolean;
  cancellation: boolean;
  resumption: boolean;
  mcp: boolean;
  images: boolean;
};

export type RuntimeStatus = {
  runtime_id: string;
  implementation_version?: string | null;
  protocol_type: string;
  protocol_version: string;
  capabilities: RuntimeCapabilities;
  state: string;
  start_available: boolean;
  blocked_reason?: string | null;
  active_session_count: number;
};

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export async function fetchRuntimeStatuses(fetcher: Fetcher): Promise<RuntimeStatus[]> {
  const response = await fetcher('/runtime');
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  const payload = await response.json() as { runtimes?: RuntimeStatus[] };
  return Array.isArray(payload.runtimes) ? payload.runtimes : [];
}
