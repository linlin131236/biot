import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import { existsSync } from 'node:fs';
import { AgentCoreSupervisor, resolveAgentCoreRuntime } from './agentCoreRuntime.js';
import { registerWorkspacePickerIpc } from './workspacePicker.js';

const devServerUrl = process.env.VITE_DEV_SERVER_URL;
let agentCore: AgentCoreSupervisor | null = null;

async function createWindow() {
  const window = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
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
  const runtime = resolveAgentCoreRuntime({
    repoRoot: path.resolve(__dirname, '../../..'),
    resourcesPath: process.resourcesPath,
    packaged: app.isPackaged,
    env: process.env,
    exists: existsSync
  });
  agentCore = new AgentCoreSupervisor({ runtime });
  const status = await agentCore.ensureStarted();
  if (status.status === 'down') console.error(status.error);
}

app.whenReady().then(async () => {
  registerWorkspacePickerIpc(ipcMain, dialog);
  await startAgentCore();
  await createWindow();
});

app.on('before-quit', () => {
  agentCore?.stop();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
