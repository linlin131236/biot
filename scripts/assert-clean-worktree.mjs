import { spawnSync } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export function inspectGitWorktree(statusPorcelain) {
  const lines = statusPorcelain
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .filter((line) => {
      const ignored = [
        '.claude/',
        '.review-tmp/',
        '.superpowers/',
        'mockup-chat-ui.html',
        'apps/desktop/src/assets/',
        'docs/superpowers/plans/2026-07-10-dbolt-',
        'docs/superpowers/plans/2026-07-10-desktop-settings.md',
        'docs/superpowers/plans/2026-07-10-provider-contracts.md',
      ];
      return !ignored.some((marker) => line.includes(marker));
    });
  return {
    dirty: lines.length > 0,
    entries: lines,
  };
}

export function assertCleanWorktreeForReleaseEvidence(statusPorcelain) {
  const result = inspectGitWorktree(statusPorcelain);
  if (result.dirty) {
    const sample = result.entries.slice(0, 20).join('\n');
    throw new Error(
      `dirty_worktree_forbidden_for_release_evidence\n${sample}${result.entries.length > 20 ? '\n...' : ''}`,
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
