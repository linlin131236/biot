import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  assertSingleProductVersion,
  validateElectronBuilderConfig,
} from './check-desktop-package-config.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));

function readJson(rel) {
  return JSON.parse(readFileSync(join(root, rel), 'utf8'));
}

test('product versions in root and desktop package.json must match', () => {
  const rootPkg = readJson('package.json');
  const desktopPkg = readJson('apps/desktop/package.json');
  assert.equal(assertSingleProductVersion(rootPkg.version, desktopPkg.version), desktopPkg.version);
  assert.throws(
    () => assertSingleProductVersion('0.1.0', '0.2.0'),
    /single product version/,
  );
});

test('electron-builder config enforces windows package policy', () => {
  const config = readJson('apps/desktop/electron-builder.json');
  const issues = validateElectronBuilderConfig(config);
  assert.deepEqual(issues, []);
});

test('validateElectronBuilderConfig rejects publish and missing agent-core resources', () => {
  const issues = validateElectronBuilderConfig({
    appId: 'dev.bolt.desktop',
    productName: 'Bolt',
    directories: { output: 'release' },
    files: ['dist/**', 'dist-electron/**', 'package.json'],
    extraResources: [],
    win: { target: ['portable'] },
    publish: { provider: 'github' },
  });
  assert.ok(issues.some((item) => item.includes('publish')));
  assert.ok(issues.some((item) => item.includes('agent-core/src')));
  assert.ok(issues.some((item) => item.includes('nsis')));
});
