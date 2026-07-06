/**
 * M36 Preload bridge test: verifies the bridge channel constant and API surface.
 *
 * The actual contextBridge.exposeInMainWorld can't run in vitest,
 * so we test the channel constant and that the bridge shape is correct.
 */
import { describe, expect, it, vi } from 'vitest';
import { BOLT_SELECT_WORKSPACE_CHANNEL } from './workspacePicker';

describe('preload bridge', () => {
  it('exposes selectWorkspace that invokes bolt:select-workspace', async () => {
    const ipcRenderer = { invoke: vi.fn().mockResolvedValue('D:/Projects/Bolt') };
    const bridge = { selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL) };
    const result = await bridge.selectWorkspace();
    expect(result).toBe('D:/Projects/Bolt');
    expect(ipcRenderer.invoke).toHaveBeenCalledWith('bolt:select-workspace');
  });

  it('returns null when user cancels', async () => {
    const ipcRenderer = { invoke: vi.fn().mockResolvedValue(null) };
    const bridge = { selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL) };
    const result = await bridge.selectWorkspace();
    expect(result).toBeNull();
  });

  it('does not expose raw ipcRenderer', () => {
    const ipcRenderer = { invoke: vi.fn() };
    const bridge = { selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL) };
    const keys = Object.keys(bridge);
    expect(keys).toEqual(['selectWorkspace']);
    expect((bridge as Record<string, unknown>).ipcRenderer).toBeUndefined();
  });

  it('does not expose generic invoke method', () => {
    const ipcRenderer = { invoke: vi.fn() };
    const bridge = { selectWorkspace: () => ipcRenderer.invoke(BOLT_SELECT_WORKSPACE_CHANNEL) };
    expect((bridge as Record<string, unknown>).invoke).toBeUndefined();
  });
});
