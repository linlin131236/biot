import { existsSync } from 'node:fs';
import { join } from 'node:path';

const requiredDirs = [
  'apps/desktop',
  'services/agent-core',
  'packages/shared',
  'docs/exec-plans/active',
  'docs/exec-plans/completed',
  'docs/exec-plans/debt'
];

const missing = requiredDirs.filter((path) => !existsSync(join(process.cwd(), path)));

if (missing.length > 0) {
  console.error(`Missing boundary directories:\n${missing.join('\n')}`);
  process.exit(1);
}
