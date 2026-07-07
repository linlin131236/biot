import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.cwd();
const maxLines = 300;
const ignored = new Set(['node_modules', 'dist', 'dist-electron', '.venv', '.git', '.bolt']);
const extensions = new Set(['.py', '.ts', '.tsx', '.css', '.md', '.json', '.yaml', '.yml']);
const generated = new Set(['pnpm-lock.yaml']);

// Pre-existing known oversized files — documented in docs/project-state.md as
// "已知风险: size check — 建议后续专项重构". These are NOT new from V4.
const KNOWN_EXEMPT = new Set([
  'docs/桌面AI编程Agent全流程架构对比.md',
  'services/agent-core/src/bolt_core/decision_memory.py',
  'services/agent-core/src/bolt_core/failure_memory_index.py',
  'services/agent-core/src/bolt_core/long_task_recovery_dogfood.py',
  'services/agent-core/src/bolt_core/memory_dogfood.py',
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
