import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync } from 'node:fs';
import path from 'node:path';

export type DiagnosticEvent = {
  id: string;
  createdAt: string;
  component: 'renderer' | 'main' | 'agent-core' | 'startup' | 'update' | 'install';
  message: string;
  details?: Record<string, unknown>;
};

const SECRET_KEY_PATTERN = /(authorization|api[_-]?key|token|bearer|bootstrap|password|secret|pfx|private[_-]?key)/i;
const BEARER_PATTERN = /Bearer\s+[A-Za-z0-9._\-]+/gi;
const PATH_PATTERN = /[A-Za-z]:\\[^\s"']+/g;

export function redactText(input: string): string {
  return input
    .replace(BEARER_PATTERN, 'Bearer [REDACTED]')
    .replace(PATH_PATTERN, '[PATH]')
    .replace(/sk-[A-Za-z0-9]{10,}/g, '[REDACTED_KEY]');
}

export function redactValue(value: unknown, keyHint = ''): unknown {
  if (SECRET_KEY_PATTERN.test(keyHint)) return '[REDACTED]';
  if (typeof value === 'string') return redactText(value);
  if (Array.isArray(value)) return value.map((item) => redactValue(item));
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      out[key] = redactValue(nested, key);
    }
    return out;
  }
  return value;
}

export function createDiagnosticId(seed: string, now = Date.now()): string {
  return createHash('sha256').update(`${seed}:${now}`).digest('hex').slice(0, 16);
}

export class DiagnosticsStore {
  constructor(
    private readonly rootDir: string,
    private readonly options: { collectionEnabled?: boolean } = {},
  ) {}

  get collectionEnabled(): boolean {
    return this.options.collectionEnabled !== false;
  }

  setCollectionEnabled(enabled: boolean): void {
    this.options.collectionEnabled = enabled;
  }

  ensureRoot(): string {
    mkdirSync(this.rootDir, { recursive: true });
    return this.rootDir;
  }

  record(event: Omit<DiagnosticEvent, 'id' | 'createdAt'> & { id?: string; createdAt?: string }): DiagnosticEvent | null {
    if (!this.collectionEnabled) return null;
    const safe: DiagnosticEvent = {
      id: event.id ?? createDiagnosticId(event.component + event.message),
      createdAt: event.createdAt ?? new Date().toISOString(),
      component: event.component,
      message: redactText(event.message),
      details: event.details ? (redactValue(event.details) as Record<string, unknown>) : undefined,
    };
    this.ensureRoot();
    const file = path.join(this.rootDir, `crash-${safe.id}.json`);
    writeFileSync(file, `${JSON.stringify(safe, null, 2)}\n`, 'utf8');
    return safe;
  }

  list(): DiagnosticEvent[] {
    if (!existsSync(this.rootDir)) return [];
    return readdirSync(this.rootDir)
      .filter((name) => name.startsWith('crash-') && name.endsWith('.json'))
      .map((name) => JSON.parse(readFileSync(path.join(this.rootDir, name), 'utf8')) as DiagnosticEvent)
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }

  exportRedactedSummary(): string {
    const events = this.list();
    return JSON.stringify(
      {
        collectionEnabled: this.collectionEnabled,
        count: events.length,
        events,
        upload: 'disabled_by_default',
      },
      null,
      2,
    );
  }
}
