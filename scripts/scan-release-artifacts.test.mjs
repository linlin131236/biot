import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import { scanReleaseArtifacts, writeReleaseEvidence } from './scan-release-artifacts.mjs';

test('scanReleaseArtifacts fails on secrets and forbidden markers', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  try {
    writeFileSync(join(root, 'Bolt.exe'), 'binary');
    writeFileSync(join(root, '.env'), 'API_KEY=sk-this-is-a-live-looking-key-123456');
    writeFileSync(
      join(root, 'note.txt'),
      "coreUrl='http://127.0.0.1:8000'\nVITE_DEV_SERVER_URL='http://localhost:5173'\nOPENAI_API_KEY=sk-abcdefghijklmnopqrstuv",
    );
    const result = scanReleaseArtifacts(root);
    assert.equal(result.ok, false);
    assert.ok(result.findings.some((item) => item.includes('.env')));
    assert.ok(
      result.findings.some(
        (item) =>
          item.includes('core_url_config')
          || item.includes('dev_server')
          || item.includes('dotenv')
          || item.includes('openai_live_key'),
      ),
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('writeReleaseEvidence emits sha256 artifacts and sbom without absolute user paths', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  const out = mkdtempSync(join(tmpdir(), 'bolt-evidence-'));
  try {
    mkdirSync(join(root, 'resources'), { recursive: true });
    writeFileSync(join(root, 'Bolt.exe'), 'binary-content');
    writeFileSync(join(root, 'resources', 'app.asar'), 'asar');
    const scan = scanReleaseArtifacts(root);
    assert.equal(scan.ok, true, scan.findings.join('\n'));
    const evidence = writeReleaseEvidence({
      outputDir: out,
      version: '0.1.0',
      commit: 'abc123',
      packageRoot: root,
      scan,
      environment: {
        node: 'v24.0.0',
        platform: 'win32',
      },
    });
    const artifacts = JSON.parse(readFileSync(join(out, 'artifacts.json'), 'utf8'));
    assert.ok(artifacts.files.some((file) => file.path === 'Bolt.exe' && file.sha256));
    const sbom = JSON.parse(readFileSync(join(out, 'sbom.json'), 'utf8'));
    assert.equal(sbom.version, '0.1.0');
    const encoded = JSON.stringify(evidence);
    assert.ok(!encoded.includes('Users\\\\'));
  } finally {
    rmSync(root, { recursive: true, force: true });
    rmSync(out, { recursive: true, force: true });
  }
});
