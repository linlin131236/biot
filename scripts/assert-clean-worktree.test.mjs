import assert from 'node:assert/strict';
import test from 'node:test';
import { assertCleanWorktreeForReleaseEvidence, inspectGitWorktree } from './assert-clean-worktree.mjs';

test('inspectGitWorktree treats tracked and untracked product files as dirty', () => {
  const result = inspectGitWorktree(' M apps/desktop/electron/main.ts\n?? services/agent-core/src/bolt_core/x.py\n');
  assert.equal(result.dirty, true);
  assert.equal(result.entries.length, 2);
});

test('assertCleanWorktreeForReleaseEvidence allows empty status', () => {
  assert.equal(assertCleanWorktreeForReleaseEvidence(''), true);
});

test('assertCleanWorktreeForReleaseEvidence rejects dirty trees', () => {
  assert.throws(
    () => assertCleanWorktreeForReleaseEvidence(' M apps/desktop/electron/main.ts\n'),
    /dirty_worktree_forbidden_for_release_evidence/,
  );
});
