import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { lookup } from 'node:dns/promises';

const host = 'release-assets.githubusercontent.com';
const failurePattern = 'docs/failure-patterns/electron-builder-package-win-network-failure.md';
const timeoutMs = 10000;
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const localElectronDist = join(root, 'apps/desktop/node_modules/electron/dist/electron.exe');

try {
  await lookup(host);
  await fetch(`https://${host}/`, { signal: AbortSignal.timeout(timeoutMs) });
  console.log(`Release preflight passed: ${host} resolves and accepts HTTPS.`);
} catch (error) {
  if (existsSync(localElectronDist)) {
    console.log(`Release preflight degraded: ${host} unreachable, but local electronDist exists.`);
    console.log(`Continuing with offline package using ${localElectronDist}`);
    process.exitCode = 0;
  } else {
    console.error(`Release preflight failed: cannot reach ${host}.`);
    console.error(`See ${failurePattern} for repair steps.`);
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
