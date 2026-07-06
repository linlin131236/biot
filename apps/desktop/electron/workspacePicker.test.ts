/**
 * M36 Workspace picker handler: tests the extracted workspacePicker.ts logic.
 */
import { describe, expect, it, vi } from 'vitest';
import { createWorkspacePickerHandler, BOLT_SELECT_WORKSPACE_CHANNEL } from './workspacePicker';

describe('workspacePicker', () => {
  it('returns selected directory path on success', async () => {
    const dialog = { showOpenDialog: vi.fn().mockResolvedValue({ canceled: false, filePaths: ['D:/Projects/Bolt'] }) };
    const handler = createWorkspacePickerHandler(dialog as never);
    const result = await handler();
    expect(result).toBe('D:/Projects/Bolt');
  });

  it('returns null when user cancels', async () => {
    const dialog = { showOpenDialog: vi.fn().mockResolvedValue({ canceled: true, filePaths: [] }) };
    const handler = createWorkspacePickerHandler(dialog as never);
    const result = await handler();
    expect(result).toBeNull();
  });

  it('calls showOpenDialog with openDirectory only', async () => {
    const dialog = { showOpenDialog: vi.fn().mockResolvedValue({ canceled: true, filePaths: [] }) };
    const handler = createWorkspacePickerHandler(dialog as never);
    await handler();
    expect(dialog.showOpenDialog).toHaveBeenCalledWith({ properties: ['openDirectory'] });
  });

  it('returns null when filePaths is empty but not canceled', async () => {
    const dialog = { showOpenDialog: vi.fn().mockResolvedValue({ canceled: false, filePaths: [] }) };
    const handler = createWorkspacePickerHandler(dialog as never);
    const result = await handler();
    expect(result).toBeNull();
  });

  it('uses bolt:select-workspace as the IPC channel name', () => {
    expect(BOLT_SELECT_WORKSPACE_CHANNEL).toBe('bolt:select-workspace');
  });
});
