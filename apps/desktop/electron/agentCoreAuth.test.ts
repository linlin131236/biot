// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { resolveAgentCoreRuntime } from './agentCoreRuntime';

describe('agent core local auth', () => {
  it('passes only the current generation bearer through the child environment', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: {},
      exists: () => false,
      generationFactory: () => ({
        startupId: 'startup-id',
        bootstrapKey: 'bootstrap-key',
        bearerToken: 'generated-local-token',
      })
    });

    expect(runtime.authToken).toBe('generated-local-token');
    expect(runtime.env.BOLT_CORE_BEARER).toBe('generated-local-token');
    expect(runtime.env.BOLT_AGENT_CORE_TOKEN).toBeUndefined();
    expect(runtime.args).not.toContain('generated-local-token');
  });

  it('rejects inherited token values and injects only the new generation bearer', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: { BOLT_AGENT_CORE_TOKEN: 'existing-token' },
      exists: () => false,
      generationFactory: () => ({
        startupId: 'startup-id',
        bootstrapKey: 'bootstrap-key',
        bearerToken: 'generated-local-token',
      })
    });

    expect(runtime.authToken).toBe('generated-local-token');
    expect(runtime.env.BOLT_AGENT_CORE_TOKEN).toBeUndefined();
    expect(runtime.env.BOLT_CORE_BEARER).toBe('generated-local-token');
  });
});
