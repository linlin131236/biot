import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createRequire } from 'node:module';
import { normalizeAsarEntry, readAsarFile, scanReleaseArtifacts, writeReleaseEvidence } from './scan-release-artifacts.mjs';

const require = createRequire(import.meta.url);

test('normalizeAsarEntry strips leading separators and uses backslash form', () => {
  const bs = String.fromCharCode(92);
  assert.equal(normalizeAsarEntry(bs + 'dist-electron' + bs + 'main.js'), 'dist-electron' + bs + 'main.js');
  assert.equal(normalizeAsarEntry('/dist-electron/main.js'), 'dist-electron' + bs + 'main.js');
});

test('scanReleaseArtifacts fails on secrets and forbidden markers', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  try {
    writeFileSync(join(root, 'Bolt.exe'), 'binary');
    writeFileSync(join(root, '.env'), 'API_KEY=sk-this-is-a-live-looking-key-123456');
    const result = scanReleaseArtifacts(root);
    assert.equal(result.ok, false);
    assert.ok(result.findings.some((item) => item.includes('.env')));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('invalid or unlistable asar is a hard failure', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  try {
    mkdirSync(join(root, 'resources'), { recursive: true });
    writeFileSync(join(root, 'Bolt.exe'), 'binary');
    writeFileSync(join(root, 'resources', 'app.asar'), 'not-a-real-asar');
    const result = scanReleaseArtifacts(root);
    assert.equal(result.ok, false);
    assert.ok(result.findings.includes('asar_listing_unavailable'));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('real asar fixture with embedded secret is detected via content scan', async () => {
  const asar = require(join(process.cwd(), 'node_modules/.pnpm/@electron+asar@3.4.1/node_modules/@electron/asar'));
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  const src = mkdtempSync(join(tmpdir(), 'bolt-asar-src-'));
  try {
    mkdirSync(join(root, 'resources'), { recursive: true });
    writeFileSync(join(root, 'Bolt.exe'), 'binary');
    writeFileSync(join(src, 'leaky.js'), ['const token = "sk-abcdefghijklmnopqrstuvwx";', 'export default token;', ''].join(String.fromCharCode(10)));
    writeFileSync(join(src, 'clean.js'), 'export const ok = true;' + String.fromCharCode(10));
    const asarPath = join(root, 'resources', 'app.asar');
    await asar.createPackage(src, asarPath);
    const bytes = readAsarFile(asarPath, 'leaky.js');
    assert.ok(bytes && bytes.length > 0);
    const result = scanReleaseArtifacts(root);
    assert.equal(result.ok, false);
    assert.ok(result.findings.some((item) => item.includes('openai_live_key') && item.includes('leaky.js')));
  } finally {
    rmSync(root, { recursive: true, force: true });
    rmSync(src, { recursive: true, force: true });
  }
});

test('writeReleaseEvidence emits sha256 artifacts and honest sbom for packages without asar', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-scan-'));
  const out = mkdtempSync(join(tmpdir(), 'bolt-evidence-'));
  try {
    mkdirSync(join(root, 'resources'), { recursive: true });
    writeFileSync(join(root, 'Bolt.exe'), 'binary-content');
    const scan = scanReleaseArtifacts(root);
    assert.equal(scan.ok, true, scan.findings.join(String.fromCharCode(10)));
    writeReleaseEvidence({ outputDir: out, version: '0.1.0', commit: 'abc123', packageRoot: root, scan, environment: { node: 'v24.0.0', platform: 'win32' } });
    const artifacts = JSON.parse(readFileSync(join(out, 'artifacts.json'), 'utf8'));
    assert.ok(artifacts.files.some((file) => file.path === 'Bolt.exe' && file.sha256));
  } finally {
    rmSync(root, { recursive: true, force: true });
    rmSync(out, { recursive: true, force: true });
  }
});
