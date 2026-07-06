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
  'docs/decisions/014-core-autonomy.md',
  'docs/decisions/015-release-hardening.md',
  'docs/decisions/016-real-workspace-runtime.md',
  'docs/decisions/017-desktop-runtime-orchestration.md',
  'docs/decisions/018-packaged-runtime-smoke.md',
  'docs/failure-patterns/README.md',
  'docs/exec-plans/active/012-desktop-shipability.md',
  'docs/exec-plans/active/013-desktop-agent-workflow.md',
  'docs/exec-plans/active/014-core-autonomy.md',
  'docs/exec-plans/active/015-release-hardening.md',
  'docs/exec-plans/active/016-real-workspace-runtime.md',
  'docs/exec-plans/active/017-desktop-runtime-orchestration.md',
  'docs/exec-plans/active/018-packaged-runtime-smoke.md',
  'docs/exec-plans/active/019-real-llm-integration.md',
  'docs/exec-plans/active/020-core-tool-expansion.md',
  'docs/exec-plans/active/021-vector-memory.md',
  'docs/exec-plans/active/022-multi-agent-delegation.md',
  'docs/exec-plans/active/023-multi-turn-conversation.md',
  'docs/exec-plans/active/024-gateway-platform.md',
  'docs/exec-plans/active/025-skill-system.md',
  'docs/exec-plans/active/026-universal-provider-moa.md',
  'docs/exec-plans/active/027-intelligent-features.md',
  'docs/exec-plans/active/028-goal-mode.md',
  'docs/exec-plans/active/029-agent-product-convergence.md',
  'docs/decisions/029-agent-product-convergence.md',
  'docs/exec-plans/active/031-integration-smoke.md',
  'docs/decisions/031-integration-smoke.md',
  'docs/exec-plans/active/032-desktop-dogfood-smoke.md',
  'docs/decisions/032-desktop-dogfood-smoke.md',
  'docs/exec-plans/active/033-ui-workflow-dogfood.md',
  'docs/decisions/033-ui-workflow-dogfood.md',
  'docs/exec-plans/active/034-chinese-desktop-quality.md',
  'docs/decisions/034-chinese-desktop-quality.md',
  'docs/exec-plans/active/035-real-workspace-binding.md',
  'docs/decisions/035-real-workspace-binding.md',
  'docs/exec-plans/active/036-native-workspace-picker.md',
  'docs/decisions/036-native-workspace-picker.md',
  'docs/exec-plans/active/037-desktop-goal-console.md',
  'docs/decisions/037-desktop-goal-console.md',
  'docs/exec-plans/active/038-goal-timeline-resume.md',
  'docs/decisions/038-goal-timeline-resume.md',
  'docs/user-guide/first-run.md',
  'docs/user-guide/windows-install.md',
  'docs/release/release-checklist.md'
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
