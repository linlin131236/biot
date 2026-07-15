import { existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REQUIRED_RELATIVE = [
  'Bolt.exe',
  'resources/app.asar',
  'resources/agent-core/src/bolt_core/app.py',
  'resources/agent-core/pyproject.toml',
  'resources/agent-core/.venv/Scripts/python.exe',
  'resources/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/bin/hermes-acp.exe',
  'resources/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/licenses/HERMES-AGENT-MIT.txt',
  'resources/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/metadata/provenance.json',
];

export function inspectPackagedWindowsTree(unpackedRoot) {
  const failures = [];
  const checks = {
    'package.layout': 'passed',
    'startup.core-resources': 'passed',
  };

  if (!unpackedRoot || !existsSync(unpackedRoot)) {
    return {
      ok: false,
      failures: [`missing win-unpacked root: ${unpackedRoot ?? '<empty>'}`],
      checks: {
        'package.layout': 'failed',
        'startup.core-resources': 'failed',
      },
    };
  }

  for (const rel of REQUIRED_RELATIVE) {
    const full = join(unpackedRoot, rel);
    if (!existsSync(full)) {
      failures.push(`missing ${rel}`);
    } else if (rel.endsWith('.exe') || rel.endsWith('.asar') || rel.endsWith('.py') || rel.endsWith('.toml')) {
      const size = statSync(full).size;
      if (size <= 0) failures.push(`empty file ${rel}`);
    }
  }

  // Packaged Core must not resolve from a sibling development services tree.
  const forbiddenDevCore = join(unpackedRoot, 'services', 'agent-core');
  if (existsSync(forbiddenDevCore)) {
    failures.push('packaged tree must not embed development services/agent-core path');
  }

  if (failures.some((item) => item.includes('Bolt.exe') || item.includes('app.asar'))) {
    checks['package.layout'] = 'failed';
  }
  if (failures.some((item) => item.includes('agent-core'))) {
    checks['startup.core-resources'] = 'failed';
  }
  if (failures.length > 0 && checks['package.layout'] === 'passed' && checks['startup.core-resources'] === 'passed') {
    checks['package.layout'] = 'failed';
  }

  return { ok: failures.length === 0, failures, checks };
}

export function defaultUnpackedRoot(repoRoot) {
  return join(repoRoot, 'apps/desktop/release/win-unpacked');
}

export function main(repoRoot = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const target = process.argv.includes('--path')
    ? process.argv[process.argv.indexOf('--path') + 1]
    : defaultUnpackedRoot(repoRoot);
  const result = inspectPackagedWindowsTree(target);
  if (!result.ok) {
    console.error(`Windows packaged smoke failed:\n${result.failures.join('\n')}`);
    process.exitCode = 1;
    return result;
  }
  console.log(`Windows packaged smoke passed: ${target}`);
  console.log(JSON.stringify({ checks: result.checks }, null, 2));
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
