import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import {
  evaluateSignatureResult,
  hasSigningMaterial,
  verifyWindowsSignature,
} from './verify-windows-signature.mjs';

test('hasSigningMaterial requires both CSC_LINK and CSC_KEY_PASSWORD', () => {
  assert.equal(hasSigningMaterial({}), false);
  assert.equal(hasSigningMaterial({ CSC_LINK: 'x' }), false);
  assert.equal(hasSigningMaterial({ CSC_KEY_PASSWORD: 'y' }), false);
  assert.equal(hasSigningMaterial({ CSC_LINK: 'x', CSC_KEY_PASSWORD: 'y' }), true);
});

test('evaluateSignatureResult never promotes unsigned builds to passed', () => {
  assert.deepEqual(
    evaluateSignatureResult({ materialPresent: false, verifyExitCode: null, stdout: '', stderr: '' }),
    {
      status: 'blocked',
      checkId: 'signing.verify',
      reason: 'release_signing_blocked',
      playerBetaAllowed: false,
    },
  );
  assert.deepEqual(
    evaluateSignatureResult({ materialPresent: true, verifyExitCode: 1, stdout: '', stderr: 'failed' }),
    {
      status: 'failed',
      checkId: 'signing.verify',
      reason: 'signtool_verify_failed',
      playerBetaAllowed: false,
      detail: 'failed',
    },
  );
  assert.equal(
    evaluateSignatureResult({ materialPresent: true, verifyExitCode: 0, stdout: 'Successfully verified', stderr: '' }).status,
    'passed',
  );
});

test('verifyWindowsSignature blocks when certificate env is absent', async () => {
  const root = mkdtempSync(join(tmpdir(), 'bolt-sign-'));
  try {
    const target = join(root, 'Bolt.exe');
    writeFileSync(target, 'stub');
    const result = await verifyWindowsSignature({
      targetPath: target,
      env: {},
      runSigntool: async () => {
        throw new Error('signtool should not run without material');
      },
    });
    assert.equal(result.status, 'blocked');
    assert.equal(result.reason, 'release_signing_blocked');
    assert.equal(result.playerBetaAllowed, false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
