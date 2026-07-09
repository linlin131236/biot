import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.cwd();
const maxLines = 300;
const ignored = new Set(['node_modules', 'dist', 'dist-electron', '.venv', '.git', '.bolt']);
const extensions = new Set(['.py', '.ts', '.tsx', '.css', '.md', '.json', '.yaml', '.yml']);
const generated = new Set(['pnpm-lock.yaml']);

// Known oversized files are temporary, documented risks. Do not add new entries
// without also documenting why the file is exempt and when it should be split.
const KNOWN_EXEMPT = new Set([
  'docs/桌面AI编程Agent全流程架构对比.md',
  'services/agent-core/src/bolt_core/decision_memory.py',
  'services/agent-core/src/bolt_core/failure_memory_index.py',
  'services/agent-core/src/bolt_core/long_task_recovery_dogfood.py',
  'services/agent-core/src/bolt_core/memory_dogfood.py',
  'apps/desktop/src/harnessClientAutonomy.ts',
  // V6 P1: M108 approval apply engine (gated write + diff parsing, single concern, split candidate)
  'services/agent-core/src/bolt_core/approval_apply.py',
  // V6 P1: M108 test file (16 tests covering full security surface, split candidate)
  'services/agent-core/tests/test_approval_apply.py',
  // M151: settings surface data (static product copy, single concern)
  'apps/desktop/src/LiquidGlassSettingsData.tsx',
  // M158: task closure service test (many service-level test cases, split candidate)
  'services/agent-core/tests/test_task_closure_service.py',
  // M161: project-state.md grows with each milestone (accumulated state record)
  'docs/project-state.md',
  // M164: app.py is the central router registry (one import/registration per feature module)
  'services/agent-core/src/bolt_core/app.py',
]);

const failures = scan(root).filter((file) => {
  const rel = relative(root, file).replace(/\\/g, '/');
  if (KNOWN_EXEMPT.has(rel)) return false;
  return lineCount(file) > maxLines;
});

if (failures.length > 0) {
  console.error(failures.map((file) => `${lineCount(file)} ${file}`).join('\n'));
  process.exit(1);
}

function scan(dir) {
  return readdirSync(dir)
    .filter((name) => !ignored.has(name))
    .flatMap((name) => collect(join(dir, name)));
}

function collect(path) {
  const stat = statSync(path);
  if (stat.isDirectory()) return scan(path);
  if (generated.has(path.split(/[\\/]/).pop())) return [];
  return extensions.has(ext(path)) ? [path] : [];
}

function ext(path) {
  const index = path.lastIndexOf('.');
  return index === -1 ? '' : path.slice(index);
}

function lineCount(path) {
  return readFileSync(path, 'utf8').split('\n').length;
}
