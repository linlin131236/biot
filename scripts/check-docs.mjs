import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const required = [
  'AGENTS.md',
  'docs/ARCHITECTURE.md',
  'docs/DESIGN.md',
  'docs/SECURITY.md',
  'docs/QUALITY_SCORE.md',
  'docs/product-specs/bolt-v1.md',
  'docs/exec-plans/active/001-harness-foundation.md',
  'docs/exec-plans/active/002-memory-layer-foundation.md',
  'docs/exec-plans/active/003-persistent-memory-permissions.md',
  'docs/exec-plans/active/004-tool-executor-foundation.md',
  'docs/references/harness-engineering.md',
  'docs/references/mem0.md',
  'docs/design-docs/golden-principles.md',
  'docs/exec-plans/active/011-harness-engineering.md',
  'docs/decisions/011-harness-engineering.md',
  'docs/decisions/012-desktop-shipability.md',
  'docs/decisions/013-desktop-agent-workflow.md',
  'docs/failure-patterns/README.md',
  'docs/exec-plans/active/012-desktop-shipability.md',
  'docs/exec-plans/active/013-desktop-agent-workflow.md',
  'docs/user-guide/first-run.md'
];

const missing = required.filter((path) => !existsSync(join(process.cwd(), path)));

if (missing.length > 0) {
  console.error(`Missing docs:\n${missing.join('\n')}`);
  process.exit(1);
}

const agentsLines = readFileSync(join(process.cwd(), 'AGENTS.md'), 'utf8').split('\n').length;
if (agentsLines > 100) {
  console.error(`AGENTS.md must stay under 100 lines; found ${agentsLines}`);
  process.exit(1);
}
