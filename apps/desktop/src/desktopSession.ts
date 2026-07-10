export interface DesktopSession {
  completed: boolean;
  workspacePath: string;
  lastRunId: string | null;
}

export const SESSION_KEY = 'bolt.desktop.session';

const defaults: DesktopSession = {
  completed: false,
  workspacePath: '',
  lastRunId: null,
};

export function loadDesktopSession(storage: Storage = localStorage): DesktopSession {
  const raw = storage.getItem(SESSION_KEY);
  if (!raw) return { ...defaults };
  try {
    const parsed = JSON.parse(raw) as unknown;
    const session = normalize(parsed);
    if (hasLegacyCoreUrl(parsed)) {
      try {
        saveDesktopSession(session, storage);
      } catch {
        // Migration write failure must not block startup or re-expose the old value.
      }
    }
    return session;
  } catch {
    return { ...defaults };
  }
}

export function saveDesktopSession(session: DesktopSession, storage: Storage = localStorage): void {
  const safe: DesktopSession = {
    completed: session.completed === true,
    workspacePath: typeof session.workspacePath === 'string' ? session.workspacePath : '',
    lastRunId: typeof session.lastRunId === 'string' ? session.lastRunId : null,
  };
  storage.setItem(SESSION_KEY, JSON.stringify(safe));
}

function normalize(value: unknown): DesktopSession {
  if (!isRecord(value)) return { ...defaults };
  return {
    completed: value.completed === true,
    workspacePath: typeof value.workspacePath === 'string' ? value.workspacePath : '',
    lastRunId: typeof value.lastRunId === 'string' ? value.lastRunId : null,
  };
}

function hasLegacyCoreUrl(value: unknown): boolean {
  return isRecord(value) && Object.prototype.hasOwnProperty.call(value, 'coreUrl');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
