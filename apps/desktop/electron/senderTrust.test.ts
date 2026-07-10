import { describe, expect, it } from 'vitest';
import {
  expectedPackagedEntryUrl,
  isAllowedNavigationUrl,
  isTrustedDesktopSender,
} from './senderTrust';

describe('isTrustedDesktopSender exact entry boundary', () => {
  const base = {
    trustedWebContentsId: 7,
    packaged: true,
    appPath: 'C:/Program Files/Bolt/resources/app.asar',
    devServerUrl: null as string | null,
  };

  it('accepts only the exact packaged index entry', () => {
    const ok = 'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html';
    expect(isTrustedDesktopSender({ sender: { id: 7 }, senderFrame: { url: ok } }, base)).toBe(true);
    expect(expectedPackagedEntryUrl(base.appPath)).toBe('file:///c:/program files/bolt/resources/app.asar/dist/index.html');
  });

  it('rejects lookalike packaged paths and arbitrary local pages', () => {
    const attacks = [
      'file:///C:/Temp/dist/index.html',
      'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html.evil',
      'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html?x=1',
      'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html#frag',
      'file://user:pass@C:/Program%20Files/Bolt/resources/app.asar/dist/index.html',
      'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/',
    ];
    for (const url of attacks) {
      expect(isTrustedDesktopSender({ sender: { id: 7 }, senderFrame: { url } }, base), url).toBe(false);
      expect(isAllowedNavigationUrl(url, base), url).toBe(false);
    }
  });

  it('rejects untrusted webContents, missing frame, iframe parent, and non-top frames', () => {
    const ok = 'file:///C:/Program%20Files/Bolt/resources/app.asar/dist/index.html';
    expect(isTrustedDesktopSender({ sender: { id: 8 }, senderFrame: { url: ok } }, base)).toBe(false);
    expect(isTrustedDesktopSender({ sender: { id: 7 } }, base)).toBe(false);
    expect(isTrustedDesktopSender({ sender: { id: 7 }, senderFrame: { url: ok, parent: {} } }, base)).toBe(false);
    expect(isTrustedDesktopSender({ sender: { id: 7 }, senderFrame: { url: ok, top: {} } }, base)).toBe(false);
  });

  it('dev mode requires exact origin and allowed pathname, not startsWith prefix', () => {
    const opts = {
      ...base,
      packaged: false,
      devServerUrl: 'http://127.0.0.1:5173',
      allowedEntryPathnames: ['/', '/index.html'],
    };
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'http://127.0.0.1:5173/index.html' },
    }, opts)).toBe(true);
    expect(isTrustedDesktopSender({
      sender: { id: 7 },
      senderFrame: { url: 'http://127.0.0.1:5173/' },
    }, opts)).toBe(true);

    const attacks = [
      'http://127.0.0.1:51730/index.html',
      'http://127.0.0.1:5173.evil.example/index.html',
      'http://127.0.0.1:5174/index.html',
      'http://127.0.0.1:5173/index.html.evil',
      'http://user:pass@127.0.0.1:5173/index.html',
      'http://127.0.0.1:5173/index.html#x',
      'http://127.0.0.1:5173/other.html',
      'file:///C:/Temp/dist/index.html',
    ];
    for (const url of attacks) {
      expect(isTrustedDesktopSender({ sender: { id: 7 }, senderFrame: { url } }, opts), url).toBe(false);
      expect(isAllowedNavigationUrl(url, opts), url).toBe(false);
    }
  });
});
