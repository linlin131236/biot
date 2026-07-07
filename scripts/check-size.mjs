import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const maxLines = 300;
const ignored = new Set(['node_modules', 'dist', 'dist-electron', '.venv', '.git', '.bolt']);
const extensions = new Set(['.py', '.ts', '.tsx', '.css', '.md', '.json', '.yaml', '.yml']);
const generated = new Set(['pnpm-lock.yaml']);

const failures = scan(root).filter((file) => lineCount(file) > maxLines);

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
