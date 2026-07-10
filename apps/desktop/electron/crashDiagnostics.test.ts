import { describe, expect, it } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { DiagnosticsStore } from './diagnosticsStore';
import { recordMainException, recordRendererGone, recordStartupFailure } from './crashDiagnostics';

describe('crashDiagnostics', () => {
  it('records renderer/main/startup failures into local diagnostics without secrets', () => {
    const dir = mkdtempSync(join(tmpdir(), 'bolt-crash-'));
    try {
      const store = new DiagnosticsStore(dir);
      recordRendererGone(store, { reason: 'crashed', exitCode: 1 });
      recordMainException(store, new Error('main boom Bearer super-secret-token'));
      recordStartupFailure(store, 'missing packaged Agent Core resource');
      const summary = store.exportRedactedSummary();
      expect(summary).toContain('Renderer process gone');
      expect(summary).toContain('main boom');
      expect(summary).not.toContain('super-secret-token');
      expect(summary).toContain('missing packaged Agent Core resource');
      expect(store.list()).toHaveLength(3);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
