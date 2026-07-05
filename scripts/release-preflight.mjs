import { lookup } from 'node:dns/promises';

const host = 'release-assets.githubusercontent.com';
const failurePattern = 'docs/failure-patterns/electron-builder-package-win-network-failure.md';
const timeoutMs = 10000;

try {
  await lookup(host);
  await fetch(`https://${host}/`, { signal: AbortSignal.timeout(timeoutMs) });
  console.log(`Release preflight passed: ${host} resolves and accepts HTTPS.`);
} catch (error) {
  console.error(`Release preflight failed: cannot reach ${host}.`);
  console.error(`See ${failurePattern} for repair steps.`);
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
