import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERMES_RELEASE = 'runtime-releases/hermes/0.18.2';
const HERMES_INVENTORY = 'services/agent-core/src/bolt_core/runtime/hermes_release_inventory.py';
const HERMES_SOURCE_ROOT = `services/agent-core/src/bolt_core/${HERMES_RELEASE}`;
const args = new Set(process.argv.slice(2));
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const requireOutput = args.has('--require-output');
const releaseRoot = join(root, 'apps/desktop/release/win-unpacked');
const failures = [];

checkBuilderResources();
requireFile('services/agent-core/src/bolt_core/app.py');
requireFile('services/agent-core/pyproject.toml');
checkHermesPayload(join(root, HERMES_SOURCE_ROOT), 'source');
checkPackagedOutput();

if (failures.length > 0) {
  console.error(`Desktop package runtime failures:\n${failures.join('\n')}`);
  process.exit(1);
}

function checkBuilderResources() {
  const config = readJson('apps/desktop/electron-builder.json');
  const resources = config.extraResources ?? [];
  requireResource(resources, '../../services/agent-core/src', 'agent-core/src');
  requireResource(resources, '../../services/agent-core/pyproject.toml', 'agent-core/pyproject.toml');
  requireResource(resources, '../../services/agent-core/.venv', 'agent-core/.venv');
  requireFile('services/agent-core/.venv/Scripts/python.exe');
  requireFile(HERMES_INVENTORY);
}

function checkPackagedOutput() {
  if (!requireOutput) return;
  if (!existsSync(releaseRoot)) {
    failures.push('missing apps/desktop/release/win-unpacked; run a Windows package command before runtime smoke');
    return;
  }
  requireReleaseFile('resources/agent-core/src/bolt_core/app.py');
  requireReleaseFile('resources/agent-core/pyproject.toml');
  requireReleaseFile('resources/agent-core/.venv/Scripts/python.exe');
  checkHermesPayload(
    join(releaseRoot, 'resources/agent-core/src/bolt_core', HERMES_RELEASE),
    'packaged',
  );
}

function checkHermesPayload(payloadRoot, scope) {
  const expected = readHermesInventory();
  if (!existsSync(payloadRoot)) {
    failures.push(`missing ${scope} Hermes payload ${payloadRoot}`);
    return;
  }
  const actual = filesUnder(payloadRoot);
  for (const [path, expectedHash] of expected) {
    const full = join(payloadRoot, path);
    if (!existsSync(full)) {
      failures.push(`missing ${scope} Hermes runtime file ${path}`);
      continue;
    }
    const actualHash = sha256(full);
    if (actualHash !== expectedHash) {
      failures.push(`Hermes runtime SHA-256 mismatch for ${scope} file ${path}`);
    }
  }
  for (const path of actual) {
    if (!expected.has(path)) {
      failures.push(`unexpected ${scope} Hermes runtime file ${path}`);
    }
  }
}

function readHermesInventory() {
  const source = readFileSync(join(root, HERMES_INVENTORY), 'utf8');
  const entries = [...source.matchAll(/^    \('([^']+)', '([a-f0-9]{64})'\),$/gm)];
  if (entries.length === 0) {
    failures.push('Hermes release inventory is empty or malformed');
    return new Map();
  }
  return new Map(entries.map(([, path, hash]) => [path, hash]));
}

function filesUnder(directory) {
  const files = [];
  for (const name of readdirSync(directory)) {
    const full = join(directory, name);
    const relativePath = relative(directory, full).replaceAll('\\', '/');
    const linkDetails = lstatSync(full);
    if (linkDetails.isSymbolicLink()) {
      failures.push(`Hermes runtime cannot contain symlink or junction ${relativePath}`);
      continue;
    }
    const details = statSync(full);
    if (details.isDirectory()) {
      for (const nested of filesUnder(full)) files.push(join(name, nested).replaceAll('\\', '/'));
    } else if (details.isFile()) {
      files.push(relativePath);
    } else {
      failures.push(`Hermes runtime contains unsupported file ${relativePath}`);
    }
  }
  return files;
}

function sha256(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function requireResource(resources, from, to) {
  const found = resources.some((entry) => entry.from === from && entry.to === to);
  if (!found) failures.push(`electron-builder extraResources must include ${from} -> ${to}`);
}

function requireFile(path) {
  if (!existsSync(join(root, path))) failures.push(`missing ${path}`);
}

function requireReleaseFile(path) {
  if (!existsSync(join(releaseRoot, path))) failures.push(`missing packaged runtime file ${path}`);
}

function readJson(path) {
  return JSON.parse(readFileSync(join(root, path), 'utf8'));
}
