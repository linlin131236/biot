import assert from 'node:assert/strict';
import test from 'node:test';
import {
  assertCleanWorktreeForReleaseEvidence,
  inspectGitWorktree,
  isIgnoredForReleaseEvidence,
} from './assert-clean-worktree.mjs';

test('inspectGitWorktree treats tracked and untracked product files as dirty', () => {
  const result = inspectGitWorktree(' M apps/desktop/electron/main.ts' + String.fromCharCode(10) + '?? services/agent-core/src/bolt_core/x.py' + String.fromCharCode(10));
  assert.equal(result.dirty, true);
  assert.equal(result.entries.length, 2);
});

test('does not ignore production assets directory', () => {
  assert.equal(isIgnoredForReleaseEvidence('?? apps/desktop/src/assets/shipping-later.js'), false);
  const result = inspectGitWorktree('?? apps/desktop/src/assets/shipping-later.js' + String.fromCharCode(10));
  assert.equal(result.dirty, true);
});

test('assertCleanWorktreeForReleaseEvidence allows empty status', () => {
  assert.equal(assertCleanWorktreeForReleaseEvidence(''), true);
});

test('assertCleanWorktreeForReleaseEvidence rejects dirty trees', () => {
  assert.throws(
    () => assertCleanWorktreeForReleaseEvidence(' M apps/desktop/electron/main.ts' + String.fromCharCode(10)),
    /dirty_worktree_forbidden_for_release_evidence/,
  );
});
