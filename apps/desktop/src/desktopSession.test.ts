import { describe, expect, it, beforeEach } from 'vitest';
import { loadDesktopSession, saveDesktopSession } from './desktopSession';

beforeEach(() => {
  localStorage.clear();
});

describe('desktop session storage', () => {
  it('returns defaults for a fresh install', () => {
    expect(loadDesktopSession()).toEqual({ completed: false, workspacePath: '', coreUrl: 'http://localhost:8000', lastRunId: null });
  });

  it('persists non-sensitive first-run state', () => {
    saveDesktopSession({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core', lastRunId: 'run_1' });

    expect(loadDesktopSession()).toEqual({ completed: true, workspacePath: 'D:/Bolt/Bolt', coreUrl: 'http://core', lastRunId: 'run_1' });
    expect(localStorage.getItem('bolt.desktop.session')).not.toContain('api_key');
  });

  it('recovers defaults from corrupted storage', () => {
    localStorage.setItem('bolt.desktop.session', '{bad');

    expect(loadDesktopSession().completed).toBe(false);
  });
});
