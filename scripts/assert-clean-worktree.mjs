import { spawnSync } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export function inspectGitWorktree(statusPorcelain) {
  const lines = statusPorcelain
    .split(String.fromCharCode(10))
    .map((line) => line.replace(new RegExp(String.fromCharCode(13) + '$'), '').trimEnd())
    .filter(Boolean)
    .filter((line) => !isIgnoredForReleaseEvidence(line));
  return {
    dirty: lines.length > 0,
    entries: lines,
  };
}

export function isIgnoredForReleaseEvidence(line) {
  const trimmed = line.trim();
  // Only non-shipping local drafts/caches. Production source trees are never ignored.
  if (trimmed.includes('.claude/') || trimmed.includes('.review-tmp/') || trimmed.includes('.superpowers/')) {
    return true;
  }
  if (trimmed === '?? mockup-chat-ui.html') return true;
  if (trimmed === '?? docs/superpowers/plans/2026-07-10-desktop-settings.md') return true;
  if (trimmed === '?? docs/superpowers/plans/2026-07-10-provider-contracts.md') return true;
  if (trimmed.startsWith('?? docs/superpowers/plans/2026-07-10-dbolt-')) return true;
  if (trimmed.startsWith('?? docs/brand-previews/')) return true;
  return false;
}

export function assertCleanWorktreeForReleaseEvidence(statusPorcelain) {
  const result = inspectGitWorktree(statusPorcelain);
  if (result.dirty) {
    const sample = result.entries.slice(0, 20).join(String.fromCharCode(10));
    throw new Error(
      'dirty_worktree_forbidden_for_release_evidence' + String.fromCharCode(10) + sample + (result.entries.length > 20 ? String.fromCharCode(10) + '...' : ''),
    );
  }
  return true;
}

export function main(repoRoot = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const status = spawnSync('git', ['status', '--porcelain'], {
    cwd: repoRoot,
    encoding: 'utf8',
    windowsHide: true,
  });
  if (status.error) {
    console.error(status.error.message);
    process.exitCode = 1;
    return;
  }
  try {
    assertCleanWorktreeForReleaseEvidence(status.stdout ?? '');
    console.log('Release evidence worktree is clean.');
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
