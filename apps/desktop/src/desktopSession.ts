export interface DesktopSession {
  completed: boolean;
  workspacePath: string;
  coreUrl: string;
  lastRunId: string | null;
}

export const DEFAULT_CORE_URL = 'http://localhost:8000';
export const SESSION_KEY = 'bolt.desktop.session';

const defaults: DesktopSession = { completed: false, workspacePath: '', coreUrl: DEFAULT_CORE_URL, lastRunId: null };

export function loadDesktopSession(storage: Storage = localStorage): DesktopSession {
  const raw = storage.getItem(SESSION_KEY);
  if (!raw) return { ...defaults };
  try {
    return normalize(JSON.parse(raw));
  } catch {
    return { ...defaults };
  }
}

export function saveDesktopSession(session: DesktopSession, storage: Storage = localStorage): void {
  storage.setItem(SESSION_KEY, JSON.stringify(session));
}

function normalize(value: unknown): DesktopSession {
  if (!isRecord(value)) return { ...defaults };
  return {
    completed: value.completed === true,
    workspacePath: typeof value.workspacePath === 'string' ? value.workspacePath : '',
    coreUrl: typeof value.coreUrl === 'string' && value.coreUrl ? value.coreUrl : DEFAULT_CORE_URL,
    lastRunId: typeof value.lastRunId === 'string' ? value.lastRunId : null
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
