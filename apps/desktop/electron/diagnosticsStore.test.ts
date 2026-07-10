import { describe, expect, it } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { DiagnosticsStore, redactText } from './diagnosticsStore';

describe('DiagnosticsStore', () => {
  it('redacts bearer tokens, secrets keys, and absolute windows paths', () => {
    const text = redactText('Bearer abc.def.ghi path=C:\\Users\\Alice\\project sk-1234567890abcdef');
    expect(text).not.toContain('abc.def.ghi');
    expect(text).not.toContain('Alice');
    expect(text).not.toContain('sk-1234567890abcdef');
  });

  it('records local diagnostics and exports redacted summary without upload', () => {
    const dir = mkdtempSync(join(tmpdir(), 'bolt-diag-'));
    try {
      const store = new DiagnosticsStore(dir);
      const event = store.record({
        component: 'agent-core',
        message: 'Agent Core exited with Bearer super-secret-token',
        details: {
          api_key: 'sk-should-not-leak',
          path: 'C:\\Users\\Alice\\workspace',
          exitCode: 1,
        },
      });
      expect(event).not.toBeNull();
      const summary = store.exportRedactedSummary();
      expect(summary).toContain('upload');
      expect(summary).toContain('disabled_by_default');
      expect(summary).not.toContain('super-secret-token');
      expect(summary).not.toContain('sk-should-not-leak');
      expect(summary).not.toContain('Alice');
      expect(store.list()).toHaveLength(1);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it('does not write diagnostics when collection is disabled', () => {
    const dir = mkdtempSync(join(tmpdir(), 'bolt-diag-'));
    try {
      const store = new DiagnosticsStore(dir, { collectionEnabled: false });
      expect(store.record({ component: 'main', message: 'ignored' })).toBeNull();
      expect(store.list()).toHaveLength(0);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
