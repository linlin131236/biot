import assert from 'node:assert/strict';
import test from 'node:test';

import { rendererCoreUrlAuthorityViolations } from './check-architecture.mjs';

const sessionFile = 'apps/desktop/src/desktopSession.ts';
const legacyDetector = "Object.prototype.hasOwnProperty.call(value, 'coreUrl')";

test('allows only the exact legacy coreUrl purge detector in desktopSession', () => {
  assert.deepEqual(rendererCoreUrlAuthorityViolations(sessionFile, legacyDetector), []);
});

test('rejects a second coreUrl authority in desktopSession despite the legacy detector', () => {
  const source = `${legacyDetector}\nconst coreUrl = 'http://127.0.0.1:8000';`;

  assert.deepEqual(rendererCoreUrlAuthorityViolations(sessionFile, source), [
    'Renderer must not retain coreUrl',
  ]);
});
