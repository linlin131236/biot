import { describe, expect, it, vi } from 'vitest';
import { registerDiagnosticsIpc } from './diagnosticsIpc';
import { registerUpdateIpc } from './updateIpc';

describe('desktop release IPC wiring', () => {
  it('registers trusted diagnostics handlers', async () => {
    const handlers = new Map<string, Function>();
    const ipcMain = {
      handle: (channel: string, listener: Function) => {
        handlers.set(channel, listener);
      },
    };
    const store = registerDiagnosticsIpc(ipcMain as never, {
      userDataPath: 'C:/tmp/bolt-user',
      isTrustedSender: () => true,
      openPath: vi.fn().mockResolvedValue(''),
    });
    expect(handlers.has('bolt:diagnostics:export-summary')).toBe(true);
    const summary = await handlers.get('bolt:diagnostics:export-summary')!({ sender: { id: 1 } });
    expect(String(summary)).toContain('disabled_by_default');
    store.record({ component: 'main', message: 'wired' });
    const summary2 = await handlers.get('bolt:diagnostics:export-summary')!({ sender: { id: 1 } });
    expect(String(summary2)).toContain('wired');
  });

  it('registers update status and keeps production channel blocked', async () => {
    const handlers = new Map<string, Function>();
    const ipcMain = {
      handle: (channel: string, listener: Function) => {
        handlers.set(channel, listener);
      },
    };
    registerUpdateIpc(ipcMain as never, {
      isTrustedSender: () => true,
      currentVersion: '0.1.0',
      productionChannelEnabled: false,
    });
    const status = await handlers.get('bolt:update:status')!({ sender: { id: 1 } });
    expect(status.productionChannelEnabled).toBe(false);
    const check = await handlers.get('bolt:update:check')!({ sender: { id: 1 } }, {});
    expect(check).toMatchObject({ reason: 'production_update_channel_blocked' });
  });
});
