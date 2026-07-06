/**
 * Workspace picker: pure logic for Electron dialog.showOpenDialog.
 * Extracted from main process for testability.
 */

import type { BrowserWindow, OpenDialogOptions, OpenDialogReturnValue } from 'electron';

const BOLT_SELECT_WORKSPACE_CHANNEL = 'bolt:select-workspace';

export { BOLT_SELECT_WORKSPACE_CHANNEL };

export interface DialogLike {
  showOpenDialog(options: OpenDialogOptions): Promise<OpenDialogReturnValue>;
}

export function createWorkspacePickerHandler(dialog: DialogLike) {
  return async function handleSelectWorkspace(): Promise<string | null> {
    const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  };
}

export function registerWorkspacePickerIpc(ipcMain: Electron.IpcMain, dialog: DialogLike): void {
  ipcMain.handle(BOLT_SELECT_WORKSPACE_CHANNEL, createWorkspacePickerHandler(dialog));
}
