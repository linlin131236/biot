/**
 * Bolt preload bridge: exposes a narrow desktop bridge to renderer.
 *
 * SECURITY:
 * - Does NOT expose raw ipcRenderer
 * - Does NOT expose generic invoke
 * - Does NOT expose the Agent Core token to renderer JavaScript
 */

import { contextBridge, ipcRenderer } from 'electron';

const BOLT_SELECT_WORKSPACE_CHANNEL = 'bolt:select-workspace';
const agentCoreToken = process.env.BOLT_AGENT_CORE_TOKEN || null;

interface AgentCoreFetchInit {
  method?: string;
  headers?: Record<string, string> | [string, string][];
  body?: string;
}

interface AgentCoreFetchResult {
  status: number;
  statusText: string;
  headers: [string, string][];
  body: string;
}

function isTrustedAgentCoreUrl(input: string): boolean {
  try {
    const url = new URL(input);
    const loopbackHosts = new Set(['localhost', '127.0.0.1', '::1', '[::1]']);
    return (url.protocol === 'http:' || url.protocol === 'https:') && loopbackHosts.has(url.hostname);
  } catch {
    return false;
  }
}

async function agentCoreFetch(input: string, init?: AgentCoreFetchInit): Promise<AgentCoreFetchResult> {
  if (!isTrustedAgentCoreUrl(input)) {
    throw new Error('Agent Core 地址必须是本机地址');
  }

  const headers = new Headers(init?.headers);
  if (agentCoreToken && !headers.has('authorization')) {
    headers.set('authorization', `Bearer ${agentCoreToken}`);
  }

  const response = await fetch(input, {
    method: init?.method,
    headers,
    body: init?.body,
  });

  return {
    status: response.status,
    statusText: response.statusText,
    headers: Array.from(response.headers.entries()),
    body: await response.text(),
  };
}

contextBridge.exposeInMainWorld('bolt', {
  selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL),
  agentCoreFetch,
});
