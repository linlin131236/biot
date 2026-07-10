import { describe, expect, it, beforeEach } from 'vitest';
import { loadDesktopSession, saveDesktopSession, SESSION_KEY } from './desktopSession';

beforeEach(() => {
  localStorage.clear();
});

describe('desktop session storage', () => {
  it('returns defaults for a fresh install without coreUrl', () => {
    expect(loadDesktopSession()).toEqual({
      completed: false,
      workspacePath: '',
      lastRunId: null,
    });
    expect(loadDesktopSession()).not.toHaveProperty('coreUrl');
  });

  it('persists non-sensitive first-run state without coreUrl', () => {
    saveDesktopSession({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_1',
    });

    expect(loadDesktopSession()).toEqual({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_1',
    });
    const raw = localStorage.getItem(SESSION_KEY) ?? '';
    expect(raw).not.toContain('api_key');
    expect(raw).not.toContain('coreUrl');
    expect(raw).not.toContain('http://');
  });

  it('physically purges legacy coreUrl from storage on successful load', () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        completed: true,
        workspacePath: 'C:/Projects/Bolt',
        coreUrl: 'https://attacker.example',
        lastRunId: 'run_legacy',
      }),
    );

    const session = loadDesktopSession();

    expect(session).toEqual({
      completed: true,
      workspacePath: 'C:/Projects/Bolt',
      lastRunId: 'run_legacy',
    });
    expect(session).not.toHaveProperty('coreUrl');
    const raw = localStorage.getItem(SESSION_KEY) ?? '';
    expect(raw).not.toContain('coreUrl');
    expect(raw).not.toContain('attacker.example');
  });

  it('does not expose coreUrl in memory when migration write fails', () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        completed: true,
        workspacePath: 'C:/Projects/Bolt',
        coreUrl: 'https://attacker.example',
        lastRunId: 'run_legacy',
      }),
    );
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function setItem(key: string, value: string) {
      if (key === SESSION_KEY && value.includes('"completed":true')) {
        throw new Error('quota exceeded');
      }
      return original.call(this, key, value);
    };
    try {
      // reload path uses getItem only first; force parse path:
      const session = loadDesktopSession();
      expect(session).not.toHaveProperty('coreUrl');
      expect(JSON.stringify(session)).not.toContain('attacker.example');
    } finally {
      Storage.prototype.setItem = original;
    }
  });

  it('recovers defaults from corrupted storage', () => {
    localStorage.setItem(SESSION_KEY, '{bad');
    expect(loadDesktopSession().completed).toBe(false);
  });
});
