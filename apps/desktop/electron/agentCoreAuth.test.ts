// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { resolveAgentCoreRuntime } from './agentCoreRuntime';

describe('agent core local auth', () => {
  it('generates a local token and passes it only through environment', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: {},
      exists: () => false,
      tokenFactory: () => 'generated-local-token'
    });

    expect(runtime.authToken).toBe('generated-local-token');
    expect(runtime.env.BOLT_AGENT_CORE_TOKEN).toBe('generated-local-token');
    expect(runtime.args).not.toContain('generated-local-token');
  });

  it('honors an explicit local token from the environment', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: { BOLT_AGENT_CORE_TOKEN: 'existing-token' },
      exists: () => false,
      tokenFactory: () => 'generated-local-token'
    });

    expect(runtime.authToken).toBe('existing-token');
    expect(runtime.env.BOLT_AGENT_CORE_TOKEN).toBe('existing-token');
  });
});
