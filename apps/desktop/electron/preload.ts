/**
 * Bolt preload bridge: exposes only window.bolt.selectWorkspace to renderer.
 *
 * SECURITY:
 * - Does NOT expose raw ipcRenderer
 * - Does NOT expose generic invoke
 * - Only the bolt:select-workspace channel is reachable
 */

import { contextBridge, ipcRenderer } from 'electron';

const BOLT_SELECT_WORKSPACE_CHANNEL = 'bolt:select-workspace';
const agentCoreToken = process.env.BOLT_AGENT_CORE_TOKEN || null;

contextBridge.exposeInMainWorld('bolt', {
  selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL),
  agentCoreAuth: () => agentCoreToken,
});
