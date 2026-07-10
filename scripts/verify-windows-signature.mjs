import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync as spawnSyncChild } from 'node:child_process';

export function hasSigningMaterial(env = process.env) {
  return Boolean(env.CSC_LINK && env.CSC_KEY_PASSWORD);
}

export function evaluateSignatureResult({ materialPresent, verifyExitCode, stdout, stderr }) {
  if (!materialPresent) {
    return {
      status: 'blocked',
      checkId: 'signing.verify',
      reason: 'release_signing_blocked',
      playerBetaAllowed: false,
    };
  }
  if (verifyExitCode !== 0) {
    return {
      status: 'failed',
      checkId: 'signing.verify',
      reason: 'signtool_verify_failed',
      playerBetaAllowed: false,
      detail: summarize(stdout, stderr),
    };
  }
  return {
    status: 'passed',
    checkId: 'signing.verify',
    reason: 'signtool_verify_ok',
    playerBetaAllowed: true,
    detail: summarize(stdout, stderr),
  };
}

export async function verifyWindowsSignature(options) {
  const {
    targetPath,
    env = process.env,
    runSigntool = defaultRunSigntool,
  } = options;
  if (!targetPath || !existsSync(targetPath)) {
    return {
      status: 'failed',
      checkId: 'signing.verify',
      reason: 'target_missing',
      playerBetaAllowed: false,
      detail: `missing ${targetPath ?? '<empty>'}`,
    };
  }
  if (!hasSigningMaterial(env)) {
    return evaluateSignatureResult({ materialPresent: false, verifyExitCode: null, stdout: '', stderr: '' });
  }
  const { code, stdout, stderr } = await runSigntool(targetPath);
  return evaluateSignatureResult({
    materialPresent: true,
    verifyExitCode: code,
    stdout,
    stderr,
  });
}

function summarize(stdout = '', stderr = '') {
  const text = `${stdout}\n${stderr}`.trim();
  // Never echo env-derived secrets; only keep a short verify summary.
  return text.slice(0, 500);
}

async function defaultRunSigntool(targetPath) {
  const result = spawnSyncChild('signtool', ['verify', '/pa', targetPath], {
    encoding: 'utf8',
    windowsHide: true,
  });
  if (result.error && result.error.code === 'ENOENT') {
    return {
      code: 1,
      stdout: '',
      stderr: 'signtool_not_found',
    };
  }
  return {
    code: result.status ?? 1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
  };
}

export async function main(repoRoot = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const targetArgIndex = process.argv.indexOf('--path');
  const targetPath = targetArgIndex >= 0
    ? process.argv[targetArgIndex + 1]
    : join(repoRoot, 'apps/desktop/release/win-unpacked/Bolt.exe');
  const result = await verifyWindowsSignature({ targetPath });
  console.log(JSON.stringify(result, null, 2));
  if (result.status !== 'passed') process.exitCode = result.status === 'blocked' ? 2 : 1;
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
