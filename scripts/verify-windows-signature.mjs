import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync as spawnSyncChild } from 'node:child_process';

export function hasSigningMaterial(env = process.env) {
  return Boolean(env.CSC_LINK && env.CSC_KEY_PASSWORD);
}

export function evaluateSignatureVerification({ targetExists, verifyExitCode, stdout = '', stderr = '' }) {
  if (!targetExists) {
    return {
      status: 'failed',
      checkId: 'signing.verify',
      reason: 'target_missing',
      playerBetaAllowed: false,
    };
  }
  if (verifyExitCode === null) {
    return {
      status: 'blocked',
      checkId: 'signing.verify',
      reason: 'signtool_unavailable',
      playerBetaAllowed: false,
      detail: summarize(stdout, stderr),
    };
  }
  if (verifyExitCode !== 0) {
    return {
      status: 'failed',
      checkId: 'signing.verify',
      reason: 'signature_missing_or_invalid',
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

export function evaluateSigningCapability({ materialPresent }) {
  if (!materialPresent) {
    return {
      status: 'blocked',
      checkId: 'signing.capability',
      reason: 'release_signing_blocked',
      canSignNewArtifacts: false,
    };
  }
  return {
    status: 'passed',
    checkId: 'signing.capability',
    reason: 'signing_material_present',
    canSignNewArtifacts: true,
  };
}

// Backward-compatible alias used by older tests/callers.
export function evaluateSignatureResult({ materialPresent, verifyExitCode, stdout = '', stderr = '' }) {
  if (!materialPresent) {
    return evaluateSigningCapability({ materialPresent: false });
  }
  return evaluateSignatureVerification({
    targetExists: true,
    verifyExitCode,
    stdout,
    stderr,
  });
}

export async function verifyWindowsSignature(options) {
  const {
    targetPath,
    env = process.env,
    runSigntool = defaultRunSigntool,
  } = options;
  const targetExists = Boolean(targetPath && existsSync(targetPath));
  const capability = evaluateSigningCapability({ materialPresent: hasSigningMaterial(env) });
  if (!targetExists) {
    return {
      ...evaluateSignatureVerification({ targetExists: false, verifyExitCode: 1 }),
      capability,
      playerBetaAllowed: false,
    };
  }
  const { code, stdout, stderr, unavailable } = await runSigntool(targetPath);
  const verification = evaluateSignatureVerification({
    targetExists: true,
    verifyExitCode: unavailable ? null : code,
    stdout,
    stderr,
  });
  return {
    ...verification,
    capability,
    playerBetaAllowed: verification.status === 'passed' && capability.status === 'passed',
  };
}

function summarize(stdout = '', stderr = '') {
  return `${stdout}\n${stderr}`.trim().slice(0, 500);
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
      unavailable: true,
    };
  }
  return {
    code: result.status ?? 1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    unavailable: false,
  };
}

export async function main(repoRoot = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const targetArgIndex = process.argv.indexOf('--path');
  const targetPath = targetArgIndex >= 0
    ? process.argv[targetArgIndex + 1]
    : join(repoRoot, 'apps/desktop/release/win-unpacked/Bolt.exe');
  const result = await verifyWindowsSignature({ targetPath });
  console.log(JSON.stringify(result, null, 2));
  if (result.status === 'passed') process.exitCode = 0;
  else if (result.status === 'blocked') process.exitCode = 2;
  else process.exitCode = 1;
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
