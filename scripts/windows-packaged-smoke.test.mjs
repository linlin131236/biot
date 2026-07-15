import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import { inspectPackagedWindowsTree } from './windows-packaged-smoke.mjs';

test('inspectPackagedWindowsTree fails when Bolt.exe or agent-core is missing', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-smoke-'));
  try {
    const result = inspectPackagedWindowsTree(root);
    assert.equal(result.ok, false);
    assert.ok(result.failures.some((item) => item.includes('Bolt.exe')));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('inspectPackagedWindowsTree passes a minimal valid package tree', () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-smoke-'));
  try {
    writeFileSync(join(root, 'Bolt.exe'), 'stub');
    mkdirSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core'), { recursive: true });
    mkdirSync(join(root, 'resources', 'agent-core', '.venv', 'Scripts'), { recursive: true });
    writeFileSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'app.py'), '# app');
    writeFileSync(join(root, 'resources', 'agent-core', 'pyproject.toml'), '[project]\nname="bolt"');
    writeFileSync(join(root, 'resources', 'agent-core', '.venv', 'Scripts', 'python.exe'), 'stub');
    mkdirSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'bin'), { recursive: true });
    mkdirSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'licenses'), { recursive: true });
    mkdirSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'metadata'), { recursive: true });
    writeFileSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'bin', 'hermes-acp.exe'), 'stub');
    writeFileSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'licenses', 'HERMES-AGENT-MIT.txt'), 'MIT');
    writeFileSync(join(root, 'resources', 'agent-core', 'src', 'bolt_core', 'runtime-releases', 'hermes', '0.18.2', 'metadata', 'provenance.json'), '{}');
    writeFileSync(join(root, 'resources', 'app.asar'), 'asar-stub');
    const result = inspectPackagedWindowsTree(root);
    assert.equal(result.ok, true);
    assert.deepEqual(result.failures, []);
    assert.equal(result.checks['package.layout'], 'passed');
    assert.equal(result.checks['startup.core-resources'], 'passed');
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
