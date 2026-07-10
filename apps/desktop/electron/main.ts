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

// ESM does not expose __dirname; reconstruct it from import.meta.url.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const devServerUrl = process.env.VITE_DEV_SERVER_URL;
let agentCore: AgentCoreSupervisor | null = null;
let trustedWebContentsId: number | null = null;

async function createWindow() {
  const window = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  trustedWebContentsId = window.webContents.id;
  window.webContents.once('destroyed', () => {
    if (trustedWebContentsId === window.webContents.id) trustedWebContentsId = null;
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    const allowed = devServerUrl ? url.startsWith(devServerUrl) : url.startsWith('file://');
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
      exists: existsSync
    });
  agentCore = new AgentCoreSupervisor({ runtimeFactory });
  return agentCore.ensureStarted();
}

app.whenReady().then(async () => {
  registerWorkspacePickerIpc(ipcMain, dialog);
  registerAgentCoreIpc(ipcMain, {
    getGeneration: () => agentCore?.getVerifiedGeneration() ?? null,
    isTrustedSender: (event) => event.sender.id === trustedWebContentsId,
    fetch,
  });
  const isTrustedSender = (event: { sender: { id: number } }) => event.sender.id === trustedWebContentsId;
  registerDiagnosticsIpc(ipcMain, {
    userDataPath: app.getPath('userData'),
    isTrustedSender,
  });
  registerUpdateIpc(ipcMain, {
    isTrustedSender,
    currentVersion: app.getVersion(),
    productionChannelEnabled: false,
    coreBusy: () => agentCore?.getVerifiedGeneration() != null,
  });
  await startDesktopWindow({ startCore: startAgentCore, createWindow });
}).catch((error) => {
  console.error(error);
  app.quit();
});

app.on('before-quit', () => {
  agentCore?.stop();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
