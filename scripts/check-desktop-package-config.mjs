import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REQUIRED_RESOURCES = [
  { from: '../../services/agent-core/src', to: 'agent-core/src' },
  { from: '../../services/agent-core/pyproject.toml', to: 'agent-core/pyproject.toml' },
  { from: '../../services/agent-core/.venv', to: 'agent-core/.venv' },
];

export function assertSingleProductVersion(rootVersion, desktopVersion) {
  if (!rootVersion || !desktopVersion || rootVersion !== desktopVersion) {
    throw new Error(
      `single product version required: root=${rootVersion ?? '<missing>'} desktop=${desktopVersion ?? '<missing>'}`,
    );
  }
  return desktopVersion;
}

export function validateElectronBuilderConfig(config) {
  const issues = [];
  if (!config || typeof config !== 'object') {
    return ['electron-builder config must be an object'];
  }
  if (config.publish != null) {
    issues.push('publish must be null to forbid implicit release publishing');
  }
  if (config.directories?.output !== 'release') {
    issues.push('directories.output must be release');
  }
  const targets = normalizeWinTargets(config.win?.target);
  for (const required of ['portable', 'nsis']) {
    if (!targets.includes(required)) {
      issues.push(`win.target must include ${required}`);
    }
  }
  const resources = Array.isArray(config.extraResources) ? config.extraResources : [];
  for (const required of REQUIRED_RESOURCES) {
    const found = resources.some((entry) => entry?.from === required.from && entry?.to === required.to);
    if (!found) {
      issues.push(`extraResources must include ${required.from} -> ${required.to}`);
    }
  }
  const files = Array.isArray(config.files) ? config.files : [];
  if (files.some((entry) => String(entry).includes('agent-core'))) {
    issues.push('agent-core must be shipped via extraResources, not files');
  }
  return issues;
}

function normalizeWinTargets(target) {
  if (!target) return [];
  if (typeof target === 'string') return [target];
  if (!Array.isArray(target)) return [];
  return target.map((item) => (typeof item === 'string' ? item : item?.target)).filter(Boolean);
}

export function main(root = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const rootPkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  const desktopPkg = JSON.parse(readFileSync(join(root, 'apps/desktop/package.json'), 'utf8'));
  assertSingleProductVersion(rootPkg.version, desktopPkg.version);
  const config = JSON.parse(readFileSync(join(root, 'apps/desktop/electron-builder.json'), 'utf8'));
  const issues = validateElectronBuilderConfig(config);
  if (issues.length > 0) {
    console.error(`Desktop package config failures:\n${issues.join('\n')}`);
    process.exitCode = 1;
    return false;
  }
  console.log(`Desktop package config ok (version ${desktopPkg.version}).`);
  return true;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
