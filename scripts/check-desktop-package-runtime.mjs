import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = new Set(process.argv.slice(2));
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const requireOutput = args.has('--require-output');
const releaseRoot = join(root, 'apps/desktop/release/win-unpacked');
const failures = [];

checkBuilderResources();
requireFile('services/agent-core/src/bolt_core/app.py');
requireFile('services/agent-core/pyproject.toml');
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
}

function checkPackagedOutput() {
  if (!requireOutput) return;
  if (!existsSync(releaseRoot)) {
    failures.push('missing apps/desktop/release/win-unpacked; run package:win:dir before runtime smoke');
    return;
  }
  requireReleaseFile('resources/agent-core/src/bolt_core/app.py');
  requireReleaseFile('resources/agent-core/pyproject.toml');
  requireReleaseFile('resources/agent-core/.venv/Scripts/python.exe');
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
