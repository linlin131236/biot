import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.cwd();
const ignored = new Set(['node_modules', 'dist', 'dist-electron', '.venv', '.git', '__pycache__', '.pytest_cache']);
const sourceExts = new Set(['.py', '.ts', '.tsx', '.js', '.jsx']);
const failures = [];

for (const file of scan(root)) checkFile(file);

if (failures.length > 0) {
  console.error(`Architecture violations:\n${failures.join('\n')}`);
  process.exit(1);
}

function scan(dir) {
  return readdirSync(dir).filter((name) => !ignored.has(name)).flatMap((name) => collect(join(dir, name)));
}

function collect(path) {
  const stat = statSync(path);
  if (stat.isDirectory()) return scan(path);
  return sourceExts.has(ext(path)) ? [path] : [];
}

function checkFile(file) {
  const rel = slash(relative(root, file));
  const text = readFileSync(file, 'utf8');
  checkLayerImports(rel, text);
  checkPythonBoundaries(rel, text);
}

function checkLayerImports(rel, text) {
  for (const target of imports(text)) {
    const normalized = slash(target);
    if (rel.startsWith('apps/desktop/') && normalized.includes('services/agent-core')) fail(rel, `desktop imports agent-core: ${target}`);
    if (rel.startsWith('packages/shared/') && /(^|\.\.\/)apps\//.test(normalized)) fail(rel, `shared imports app layer: ${target}`);
    if (rel.startsWith('packages/shared/') && /(^|\.\.\/)services\//.test(normalized)) fail(rel, `shared imports service layer: ${target}`);
    if (rel.startsWith('services/agent-core/') && /(^|\.\.\/)apps\//.test(normalized)) fail(rel, `agent-core imports app layer: ${target}`);
    if (rel.startsWith('services/agent-core/') && /(^|\.\.\/)packages\//.test(normalized)) fail(rel, `agent-core imports package layer: ${target}`);
  }
}

function checkPythonBoundaries(rel, text) {
  if (!rel.startsWith('services/agent-core/src/bolt_core/') || !rel.endsWith('.py')) return;
  if (rel.endsWith('harness.py') || rel.endsWith('file_writer.py') || rel.endsWith('patch_engine.py') || rel.endsWith('atomic_write.py') || rel.endsWith('shell_executor.py') || rel.endsWith('background_executor.py') || rel.endsWith('goal_persistence.py') || rel.endsWith('checkpoint.py') || rel.endsWith('execution_audit_store.py') || rel.endsWith('release_readiness.py') || rel.endsWith('local_release_checklist.py')) return;
  // Pre-existing: subprocess only for read-only git commands (log, status)
  if (rel.endsWith('code_map_index.py') || rel.endsWith('project_profile.py')) return;
  // V6: tool ecosystem – read-only git commands and whitelisted test runner
  if (rel.endsWith('readonly_tool_runner.py') || rel.endsWith('write_tool_proposal.py') || rel.endsWith('test_runner_integration.py')) return;
  // V6 P1 fix: approval_apply.py is the gated write boundary (10 safety checks before write)
  if (rel.endsWith('approval_apply.py')) return;
  // V7 M112: patch_apply_eval.py writes in temp directories for eval (not real project files)
  if (rel.endsWith('patch_apply_eval.py')) return;
  // V7 M118: e2e_task_dogfood.py writes in temp directories for dogfood (not real project files)
  if (rel.endsWith('e2e_task_dogfood.py')) return;
  // M159: researcher_engine.py mentions "subprocess" only as a risk keyword string
  if (rel.endsWith('researcher_engine.py')) return;
  // M160: builder_engine.py imports file_writer to produce proposals (not direct writes)
  if (rel.endsWith('builder_engine.py')) return;
  // M151: desktop_settings.py writes to .bolt/ user config (settings + API key file)
  if (rel.endsWith('desktop_settings.py')) return;
  if (/from bolt_core\.(file_writer|patch_engine) import /.test(text)) fail(rel, 'direct write primitive import outside harness boundary');
  if (/\bsubprocess\b/.test(text)) fail(rel, 'subprocess usage outside shell executor boundary');
  if (/\.write_text\(|\.write_bytes\(|open\([^\n]*['"]w/.test(text)) fail(rel, 'direct file write outside write boundary');
}

function imports(text) {
  const found = [];
  for (const line of text.split('\n')) {
    const match = line.match(/(?:import|export)\s+.*?from\s+['"]([^'"]+)['"]/) || line.match(/require\(['"]([^'"]+)['"]\)/);
    if (match) found.push(match[1]);
  }
  return found;
}

function fail(rel, message) {
  failures.push(`${rel}: ${message}`);
}

function ext(path) {
  const index = path.lastIndexOf('.');
  return index === -1 ? '' : path.slice(index);
}

function slash(value) {
  return value.replaceAll('\\', '/');
}
