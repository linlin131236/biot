import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const failures = [];

const desktopPackage = readJson('apps/desktop/package.json');
const scripts = desktopPackage.scripts ?? {};

requireScript('package:win', ['node ../../scripts/assert-clean-worktree.mjs', 'node ../../scripts/check-desktop-package-config.mjs', 'node ../../scripts/run-electron-builder.mjs', '--win portable nsis', '--publish never', 'node ../../scripts/check-desktop-package-runtime.mjs --require-output']);
requireScript('package:win:portable', ['node ../../scripts/assert-clean-worktree.mjs', 'node ../../scripts/check-desktop-package-config.mjs', 'node ../../scripts/release-preflight.mjs', 'node ../../scripts/run-electron-builder.mjs', '--win portable', '--publish never', 'node ../../scripts/check-desktop-package-runtime.mjs --require-output']);
requireScript('package:win:nsis', ['node ../../scripts/assert-clean-worktree.mjs', 'node ../../scripts/check-desktop-package-config.mjs', 'node ../../scripts/release-preflight.mjs', 'node ../../scripts/run-electron-builder.mjs', '--win nsis', '--publish never', 'node ../../scripts/check-desktop-package-runtime.mjs --require-output']);
requireScript('package:win:dir', [
  'node ../../scripts/assert-clean-worktree.mjs',
  'node ../../scripts/check-desktop-package-config.mjs',
  'node ../../scripts/release-preflight.mjs',
  'node ../../scripts/run-electron-builder.mjs',
  '--win --dir',
  '--publish never',
  'node ../../scripts/check-desktop-package-runtime.mjs --require-output'
]);

requireFile('.github/workflows/release.yml');
requireFile('scripts/check-desktop-package-runtime.mjs');
if (existsSync(join(root, '.github/workflows/release.yml'))) {
  const workflow = readFileSync(join(root, '.github/workflows/release.yml'), 'utf8');
  requireText(workflow, 'workflow_dispatch', 'release workflow must be manual');
  requireText(workflow, 'package_target', 'release workflow must expose package_target');
  requireText(workflow, 'channel', 'release workflow must expose channel');
  requireText(workflow, 'actions/upload-artifact', 'release workflow must upload artifacts');
  forbidText(workflow, 'gh release create', 'release workflow must not create releases');
  forbidText(workflow, 'publish always', 'release workflow must not force publishing');
}

[
  'docs/user-guide/windows-install.md',
  'docs/release/release-checklist.md',
  'docs/decisions/015-release-hardening.md',
  'docs/exec-plans/active/015-release-hardening.md',
  'docs/decisions/018-packaged-runtime-smoke.md',
  'docs/exec-plans/active/018-packaged-runtime-smoke.md',
].forEach(requireFile);

const gitignore = readFileSync(join(root, '.gitignore'), 'utf8');
['*.pfx', '*.p12', '*.pem', '*.key'].forEach((pattern) => requireText(gitignore, pattern, `.gitignore must protect ${pattern}`));
requireText(gitignore, 'apps/desktop/release/', '.gitignore must ignore desktop release output');

if (failures.length > 0) {
  console.error(`Release policy failures:\n${failures.join('\n')}`);
  process.exit(1);
}

function readJson(path) {
  return JSON.parse(readFileSync(join(root, path), 'utf8'));
}

function requireScript(name, fragments) {
  const command = scripts[name];
  if (!command) {
    failures.push(`missing apps/desktop script: ${name}`);
    return;
  }
  fragments.forEach((fragment) => requireText(command, fragment, `${name} must include ${fragment}`));
}

function requireFile(path) {
  if (!existsSync(join(root, path))) failures.push(`missing ${path}`);
}

function requireText(content, text, message) {
  if (!content.includes(text)) failures.push(message);
}

function forbidText(content, text, message) {
  if (content.includes(text)) failures.push(message);
}
