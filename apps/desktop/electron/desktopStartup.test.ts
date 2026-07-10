// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { startDesktopWindow } from './desktopStartup';

describe('desktop startup gate', () => {
  it('does not create a BrowserWindow when initial Core verification fails', async () => {
    const createWindow = vi.fn();

    await expect(startDesktopWindow({
      startCore: vi.fn().mockResolvedValue({ status: 'down', error: 'CORE_READINESS_INVALID' }),
      createWindow,
    })).rejects.toThrow('CORE_READINESS_INVALID');

    expect(createWindow).not.toHaveBeenCalled();
  });

  it('creates the BrowserWindow only after Core is verified', async () => {
    const order: string[] = [];

    await startDesktopWindow({
      startCore: vi.fn().mockImplementation(async () => {
        order.push('verified');
        return { status: 'ok' };
      }),
      createWindow: vi.fn().mockImplementation(async () => {
        order.push('window');
      }),
    });

    expect(order).toEqual(['verified', 'window']);
  });
});
