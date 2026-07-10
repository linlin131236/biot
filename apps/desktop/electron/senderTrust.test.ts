import { describe, expect, it } from 'vitest';
import { isTrustedDesktopSender } from './senderTrust';

describe('isTrustedDesktopSender', () => {
  const base = {
    trustedWebContentsId: 7,
    packaged: true,
    appPath: 'C:/Program Files/Bolt/resources/app.asar',
    devServerUrl: null as string | null,
  };

  it('rejects untrusted webContents id', () => {
    expect(isTrustedDesktopSender({
      sender: { id: 8 },
      senderFrame: { url: 'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html' },
    }, base)).toBe(false);
  });

  it('rejects missing/non-top frames', () => {
    expect(isTrustedDesktopSender({ sender: { id: 7 } }, base)).toBe(false);
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html', parent: {} },
    }, base)).toBe(false);
  });

  it('rejects arbitrary file urls even when webContents matches', () => {
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'file:///C:/Temp/evil.html' },
    }, base)).toBe(false);
  });

  it('accepts packaged index entry with matching webContents', () => {
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html' },
    }, base)).toBe(true);
  });

  it('accepts exact dev server origin only when configured', () => {
    const opts = { ...base, packaged: false, devServerUrl: 'http://127.0.0.1:5173/' };
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'http://127.0.0.1:5173/index.html' },
    }, opts)).toBe(true);
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'http://127.0.0.1:5174/index.html' },
    }, opts)).toBe(false);
  });
});
