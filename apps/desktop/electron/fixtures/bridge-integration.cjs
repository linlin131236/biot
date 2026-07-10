const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('node:path');

const REQUEST = 'bolt:agent-core:request';
const CANCEL = 'bolt:agent-core:cancel';

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
  await window.loadURL(`data:text/html,${encodeURIComponent('<!doctype html><div id="app"></div>')}`);
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
    };
  })()`);
  process.stdout.write(`${JSON.stringify(result)}\n`);
  window.destroy();
  app.quit();
}).catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  app.exit(1);
});
