import { shell } from 'electron';
import path from 'node:path';
import { DiagnosticsStore } from './diagnosticsStore.js';

type IpcMainLike = {
  handle: (channel: string, listener: (event: unknown, ...args: unknown[]) => unknown) => void;
};

export type DiagnosticsIpcDependencies = {
  userDataPath: string;
  isTrustedSender: (event: { sender: { id: number } }) => boolean;
  openPath?: (target: string) => Promise<string>;
};

const CHANNELS = {
  exportSummary: 'bolt:diagnostics:export-summary',
  openDir: 'bolt:diagnostics:open-dir',
  setEnabled: 'bolt:diagnostics:set-enabled',
  getEnabled: 'bolt:diagnostics:get-enabled',
  record: 'bolt:diagnostics:record',
} as const;

export function createDiagnosticsStore(userDataPath: string): DiagnosticsStore {
  return new DiagnosticsStore(path.join(userDataPath, 'diagnostics'));
}

export function registerDiagnosticsIpc(
  ipcMain: IpcMainLike,
  dependencies: DiagnosticsIpcDependencies,
  store = createDiagnosticsStore(dependencies.userDataPath),
): DiagnosticsStore {
  const openPath = dependencies.openPath ?? ((target: string) => shell.openPath(target));

  ipcMain.handle(CHANNELS.exportSummary, (event) => {
    assertTrusted(event, dependencies);
    return store.exportRedactedSummary();
  });
  ipcMain.handle(CHANNELS.openDir, async (event) => {
    assertTrusted(event, dependencies);
    const dir = store.ensureRoot();
    await openPath(dir);
  });
  ipcMain.handle(CHANNELS.setEnabled, (event, enabled) => {
    assertTrusted(event, dependencies);
    store.setCollectionEnabled(Boolean(enabled));
    return store.collectionEnabled;
  });
  ipcMain.handle(CHANNELS.getEnabled, (event) => {
    assertTrusted(event, dependencies);
    return store.collectionEnabled;
  });
  ipcMain.handle(CHANNELS.record, (event, payload) => {
    assertTrusted(event, dependencies);
    const body = (payload ?? {}) as { component?: DiagnosticsStore extends never ? never : string; message?: string; details?: Record<string, unknown> };
    if (!body.component || !body.message) return null;
    return store.record({
      component: body.component as 'renderer' | 'main' | 'agent-core' | 'startup' | 'update' | 'install',
      message: body.message,
      details: body.details,
    });
  });

  return store;
}

function assertTrusted(event: unknown, dependencies: DiagnosticsIpcDependencies): void {
  const typed = event as { sender: { id: number } };
  if (!dependencies.isTrustedSender(typed)) {
    throw new Error('untrusted diagnostics sender');
  }
}

export const diagnosticsChannels = CHANNELS;
