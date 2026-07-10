/**
 * Bolt preload bridge: exposes a narrow desktop bridge to renderer.
 *
 * SECURITY:
 * - Does NOT expose raw ipcRenderer
 * - Does NOT expose generic invoke
 * - Does NOT expose the Agent Core token or endpoint
 *
 * NOTE: This file must be .cts (CommonJS TypeScript) because Electron's
 * sandboxed preload context does not support ES modules.
 */

import { contextBridge, ipcRenderer } from 'electron';

const BOLT_SELECT_WORKSPACE_CHANNEL = 'bolt:select-workspace';
const AGENT_CORE_REQUEST_CHANNEL = 'bolt:agent-core:request';
const AGENT_CORE_CANCEL_CHANNEL = 'bolt:agent-core:cancel';

interface AgentCoreRequestInit {
  method?: string;
  headers?: [string, string][];
  body?: string;
}

function agentCoreRequest(path: string, init?: AgentCoreRequestInit) {
  const requestId = createRequestId();
  const response = ipcRenderer.invoke(AGENT_CORE_REQUEST_CHANNEL, {
    requestId,
    path,
    method: init?.method ?? 'GET',
    headers: init?.headers,
    body: init?.body,
  });
  return {
    requestId,
    response,
    cancel: () => ipcRenderer.invoke(AGENT_CORE_CANCEL_CHANNEL, { requestId }),
  };
}

function createRequestId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

contextBridge.exposeInMainWorld('bolt', {
  selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL),
  agentCoreRequest,
});
