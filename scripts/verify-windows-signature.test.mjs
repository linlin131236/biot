import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import {
  evaluateSignatureVerification,
  evaluateSigningCapability,
  hasSigningMaterial,
  verifyWindowsSignature,
} from './verify-windows-signature.mjs';

test('hasSigningMaterial requires both CSC_LINK and CSC_KEY_PASSWORD', () => {
  assert.equal(hasSigningMaterial({}), false);
  assert.equal(hasSigningMaterial({ CSC_LINK: 'x', CSC_KEY_PASSWORD: 'y' }), true);
});

test('verification does not require private key material', () => {
  assert.equal(
    evaluateSignatureVerification({ targetExists: true, verifyExitCode: 0, stdout: 'ok', stderr: '' }).status,
    'passed',
  );
  assert.equal(
    evaluateSignatureVerification({ targetExists: true, verifyExitCode: 1, stdout: '', stderr: 'unsigned' }).reason,
    'signature_missing_or_invalid',
  );
});

test('signing capability is a separate gate from verification', () => {
  assert.deepEqual(evaluateSigningCapability({ materialPresent: false }).reason, 'release_signing_blocked');
  assert.equal(evaluateSigningCapability({ materialPresent: true }).canSignNewArtifacts, true);
});

test('verifyWindowsSignature runs signtool even without CSC env', async () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-sign-'));
  try {
    const target = join(root, 'Bolt.exe');
    writeFileSync(target, 'stub');
    let ran = false;
    const result = await verifyWindowsSignature({
      targetPath: target,
      env: {},
      runSigntool: async () => {
        ran = true;
        return { code: 1, stdout: '', stderr: 'NotSigned', unavailable: false };
      },
    });
    assert.equal(ran, true);
    assert.equal(result.status, 'failed');
    assert.equal(result.capability.status, 'blocked');
    assert.equal(result.playerBetaAllowed, false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
