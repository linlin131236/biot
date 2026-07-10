import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { AgentCoreSupervisor, resolveAgentCoreRuntime } from './agentCoreRuntime.js';
import { registerWorkspacePickerIpc } from './workspacePicker.js';
import { startDesktopWindow } from './desktopStartup.js';
import { registerAgentCoreIpc } from './agentCoreIpc.js';
import { registerDiagnosticsIpc } from './diagnosticsIpc.js';
import { registerUpdateIpc } from './updateIpc.js';
import { recordMainException, recordRendererGone, recordStartupFailure } from './crashDiagnostics.js';
import { isAllowedNavigationUrl, isTrustedDesktopSender } from './senderTrust.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const devServerUrl = process.env.VITE_DEV_SERVER_URL;
let agentCore: AgentCoreSupervisor | null = null;
let trustedWebContentsId: number | null = null;
let diagnosticsStore: ReturnType<typeof registerDiagnosticsIpc> | null = null;

function isTrustedSender(event: {
  sender: { id: number };
  senderFrame?: { url?: string; parent?: unknown; top?: unknown } | null;
}): boolean {
  return isTrustedDesktopSender(event, {
    trustedWebContentsId,
    packaged: app.isPackaged,
    appPath: app.getAppPath(),
    devServerUrl: devServerUrl ?? null,
    allowedEntryPathnames: ['/', '/index.html'],
  });
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  trustedWebContentsId = window.webContents.id;
  window.webContents.on('render-process-gone', (_event, details) => {
    recordRendererGone(diagnosticsStore, details);
  });
  window.webContents.on('unresponsive', () => {
    recordStartupFailure(diagnosticsStore, 'Renderer became unresponsive');
  });
  window.webContents.once('destroyed', () => {
    if (trustedWebContentsId === window.webContents.id) trustedWebContentsId = null;
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    const allowed = isAllowedNavigationUrl(url, {
      packaged: app.isPackaged,
      appPath: app.getAppPath(),
      devServerUrl: devServerUrl ?? null,
      allowedEntryPathnames: ['/', '/index.html'],
    });
    if (!allowed) event.preventDefault();
  });
  if (devServerUrl) {
    await window.loadURL(devServerUrl);
  } else {
    await window.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

async function startAgentCore() {
  const runtimeFactory = () => resolveAgentCoreRuntime({
    repoRoot: path.resolve(__dirname, '../../..'),
    resourcesPath: process.resourcesPath,
    packaged: app.isPackaged,
    env: process.env,
    exists: existsSync,
  });
  agentCore = new AgentCoreSupervisor({ runtimeFactory });
  return agentCore.ensureStarted();
}

app.whenReady().then(async () => {
  registerWorkspacePickerIpc(ipcMain, dialog);
  registerAgentCoreIpc(ipcMain, {
    getGeneration: () => agentCore?.getVerifiedGeneration() ?? null,
    isTrustedSender,
    fetch,
  });
  diagnosticsStore = registerDiagnosticsIpc(ipcMain, {
    userDataPath: app.getPath('userData'),
    isTrustedSender,
  });
  registerUpdateIpc(ipcMain, {
    isTrustedSender,
    currentVersion: app.getVersion(),
    productionChannelEnabled: false,
    coreBusy: () => agentCore?.getVerifiedGeneration() != null,
  });
  await startDesktopWindow({
    startCore: async () => {
      const status = await startAgentCore();
      if (status.status !== 'ok') {
        recordStartupFailure(diagnosticsStore, status.error ?? 'Agent Core startup failed');
      }
      return status;
    },
    createWindow,
  });
}).catch((error) => {
  recordStartupFailure(diagnosticsStore, error instanceof Error ? error.message : 'desktop startup failed');
  console.error(error);
  app.quit();
});

app.on('before-quit', () => {
  agentCore?.stop();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// Record fatals without swallowing Electron's default crash exit behavior.
process.on('uncaughtExceptionMonitor', (error) => {
  recordMainException(diagnosticsStore, error);
});

process.on('unhandledRejection', (reason) => {
  recordMainException(diagnosticsStore, reason instanceof Error ? reason : new Error('unhandledRejection'));
});
