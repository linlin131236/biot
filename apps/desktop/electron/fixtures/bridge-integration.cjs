const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('node:path');

app.disableHardwareAcceleration();
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('disable-software-rasterizer');

const REQUEST = 'bolt:agent-core:request';
const CANCEL = 'bolt:agent-core:cancel';

const hardExitTimer = setTimeout(() => {
  process.stderr.write('bridge-integration fixture hard-timeout' + String.fromCharCode(10));
  app.exit(2);
}, 12000);
if (hardExitTimer.unref) hardExitTimer.unref();

ipcMain.handle(REQUEST, async (_event, request) => ({
  requestId: request.requestId,
  generationId: 'integration-generation',
  status: 200,
  statusText: 'OK',
  headers: [['content-type', 'application/json']],
  body: '{"ok":true}',
}));
ipcMain.handle(CANCEL, async () => 'cancelled');
ipcMain.handle('bolt:select-workspace', async () => null);
ipcMain.handle('bolt:diagnostics:export-summary', async () => '{"events":[]}');
ipcMain.handle('bolt:diagnostics:open-dir', async () => undefined);
ipcMain.handle('bolt:diagnostics:set-enabled', async () => false);
ipcMain.handle('bolt:diagnostics:get-enabled', async () => true);
ipcMain.handle('bolt:diagnostics:record', async () => null);
ipcMain.handle('bolt:update:status', async () => ({ productionChannelEnabled: false }));
ipcMain.handle('bolt:update:check', async () => ({ status: 'rejected', reason: 'production_update_channel_blocked' }));

app.whenReady().then(async () => {
  const window = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', '..', 'dist-electron', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  await window.loadURL('data:text/html,' + encodeURIComponent('<!doctype html><div id="app"></div>'));
  const result = await window.webContents.executeJavaScript(`(async () => {
    const handle = window.bolt.agentCoreRequest('/memory', { method: 'GET' });
    const synchronousHandle = typeof handle.requestId === 'string' && handle.response instanceof Promise;
    const response = await handle.response;
    const cancelResult = await handle.cancel();
    return {
      synchronousHandle,
      promiseResponse: response.status === 200 && response.generationId === 'integration-generation',
      cancelResult,
      contextIsolated: typeof process === 'undefined' && typeof require === 'undefined',
      noEndpoint: !('agentCoreEndpoint' in window.bolt),
      noRawIpc: !('ipcRenderer' in window.bolt) && !('invoke' in window.bolt),
      hasDiagnostics: !!window.bolt.diagnostics && typeof window.bolt.diagnostics.exportSummary === 'function',
      hasUpdate: !!window.bolt.update && typeof window.bolt.update.status === 'function',
    };
  })()`);
  process.stdout.write(JSON.stringify(result) + String.fromCharCode(10));
  window.destroy();
  clearTimeout(hardExitTimer);
  app.exit(0);
}).catch((error) => {
  process.stderr.write((error && error.stack) ? error.stack : String(error));
  process.stderr.write(String.fromCharCode(10));
  clearTimeout(hardExitTimer);
  app.exit(1);
});
