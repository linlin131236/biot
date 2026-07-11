// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { resolveAgentCoreRuntime, AgentCoreSupervisor, defaultHealthCheck } from './agentCoreRuntime';

describe('agent core runtime', () => {
  it('fails closed when no trusted user data root is provided', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: { BOLT_CORE_DATA_ROOT: 'C:/attacker/data' },
      exists: () => false,
      generationFactory: () => ({
        startupId: 'startup-id',
        bootstrapKey: 'bootstrap-key',
        bearerToken: 'bearer-token',
      }),
    });

    expect(runtime.validationError).toBe('Agent Core data root is required');
    expect(runtime.env.BOLT_CORE_DATA_ROOT).toBeUndefined();
  });

  it('passes Electron userData to the Agent Core runtime factory', () => {
    const mainSource = readFileSync(join(__dirname, 'main.ts'), 'utf-8');

    expect(mainSource).toContain("dataRoot: app.getPath('userData'),");
  });

  it('strict health accepts only exact HTTP 200 liveness schema without redirects', async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"status":"ok","service":"bolt-agent-core"}', { status: 200 }));
    globalThis.fetch = fetchMock;
    try {
      await expect(defaultHealthCheck('http://127.0.0.1:43123')).resolves.toBe(true);
      expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:43123/health', expect.objectContaining({ redirect: 'error' }));
      fetchMock.mockResolvedValueOnce(new Response('{"status":"ok","service":"bolt-agent-core","extra":true}', { status: 200 }));
      await expect(defaultHealthCheck('http://127.0.0.1:43123')).resolves.toBe(false);
      fetchMock.mockResolvedValueOnce(new Response('{"status":"ok","status":"ok","service":"bolt-agent-core"}', { status: 200 }));
      await expect(defaultHealthCheck('http://127.0.0.1:43123')).resolves.toBe(false);
      fetchMock.mockResolvedValueOnce(new Response('{"status":"ok","\\u0073tatus":"ok","service":"bolt-agent-core"}', { status: 200 }));
      await expect(defaultHealthCheck('http://127.0.0.1:43123')).resolves.toBe(false);
      fetchMock.mockResolvedValueOnce(new Response('{"status":"ok","service":"bolt-agent-core"}', { status: 500 }));
      await expect(defaultHealthCheck('http://127.0.0.1:43123')).resolves.toBe(false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('revokes the verified generation immediately when the child exits', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean; pid: number };
    child.kill = vi.fn();
    child.killed = false;
    child.pid = 1234;
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {},
      exists: () => false,
    });
    const supervisor = new AgentCoreSupervisor({
      runtime,
      readiness: vi.fn().mockResolvedValue({ generationId: runtime.startupId, endpoint: 'http://127.0.0.1:43123', port: 43123 }),
      health: vi.fn().mockResolvedValue(true),
      spawn: vi.fn().mockReturnValue(child),
    });
    await supervisor.ensureStarted();

    child.emit('exit', 1, null);

    expect(supervisor.getVerifiedGeneration()).toBeNull();
  });

  it('creates fresh startup bootstrap and bearer secrets for every child restart', async () => {
    const children = [1, 2].map((pid) => {
      const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean; pid: number };
      child.kill = vi.fn();
      child.killed = false;
      child.pid = pid;
      return child;
    });
    const generations = [
      { startupId: 'startup-one', bootstrapKey: 'bootstrap-one', bearerToken: 'bearer-one' },
      { startupId: 'startup-two', bootstrapKey: 'bootstrap-two', bearerToken: 'bearer-two' },
    ];
    let generationIndex = 0;
    const runtimeFactory = () => resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {},
      exists: () => false,
      generationFactory: () => generations[generationIndex++],
    });
    const spawn = vi.fn()
      .mockReturnValueOnce(children[0])
      .mockReturnValueOnce(children[1]);
    const readiness = vi.fn(async (_child, runtime) => ({
      generationId: runtime.startupId,
      endpoint: runtime.startupId === 'startup-one'
        ? 'http://127.0.0.1:43123'
        : 'http://127.0.0.1:43124',
      port: runtime.startupId === 'startup-one' ? 43123 : 43124,
    }));
    const supervisor = new AgentCoreSupervisor({
      runtimeFactory,
      readiness,
      health: vi.fn().mockResolvedValue(true),
      spawn,
    });

    await supervisor.ensureStarted();
    const first = supervisor.getVerifiedGeneration();
    children[0].emit('exit', 1, null);
    expect(supervisor.getVerifiedGeneration()).toBeNull();
    await supervisor.ensureStarted();
    const second = supervisor.getVerifiedGeneration();

    expect(first).toEqual({
      generationId: 'startup-one',
      endpoint: 'http://127.0.0.1:43123',
      bearerToken: 'bearer-one',
    });
    expect(second).toEqual({
      generationId: 'startup-two',
      endpoint: 'http://127.0.0.1:43124',
      bearerToken: 'bearer-two',
    });
    const firstEnv = spawn.mock.calls[0][2].env;
    const secondEnv = spawn.mock.calls[1][2].env;
    expect(firstEnv.BOLT_CORE_STARTUP_ID).toBe('startup-one');
    expect(firstEnv.BOLT_CORE_BOOTSTRAP_KEY).toBe('bootstrap-one');
    expect(firstEnv.BOLT_CORE_BEARER).toBe('bearer-one');
    expect(secondEnv.BOLT_CORE_STARTUP_ID).toBe('startup-two');
    expect(secondEnv.BOLT_CORE_BOOTSTRAP_KEY).toBe('bootstrap-two');
    expect(secondEnv.BOLT_CORE_BEARER).toBe('bearer-two');
  });

  it('requires authenticated readiness before health and exposes only the verified generation', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean; pid: number };
    child.kill = vi.fn();
    child.killed = false;
    child.pid = 1234;
    const health = vi.fn().mockResolvedValue(true);
    const readiness = vi.fn().mockResolvedValue({
      generationId: 'verified-generation',
      endpoint: 'http://127.0.0.1:43123',
      port: 43123,
    });
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {},
      exists: () => false,
      generationFactory: () => ({
        startupId: 'verified-generation',
        bootstrapKey: 'bootstrap',
        bearerToken: 'bearer',
      }),
    });
    const supervisor = new AgentCoreSupervisor({
      runtime,
      readiness,
      health,
      spawn: vi.fn().mockReturnValue(child),
    });

    const status = await supervisor.ensureStarted();

    expect(readiness).toHaveBeenCalledWith(child, runtime);
    expect(health).toHaveBeenCalledWith('http://127.0.0.1:43123');
    expect(status).toEqual({
      status: 'ok',
      started: true,
      baseUrl: 'http://127.0.0.1:43123',
    });
    expect(supervisor.getVerifiedGeneration()).toEqual({
      generationId: 'verified-generation',
      endpoint: 'http://127.0.0.1:43123',
      bearerToken: 'bearer',
    });
  });

  it('never adopts an already healthy localhost service before readiness proof', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean; pid: number };
    child.kill = vi.fn();
    child.killed = false;
    child.pid = 1234;
    const spawn = vi.fn().mockReturnValue(child);
    const health = vi.fn().mockResolvedValue(true);
    const readiness = vi.fn().mockRejectedValue(new Error('CORE_READINESS_INVALID'));
    const supervisor = new AgentCoreSupervisor({
      runtime: resolveAgentCoreRuntime({ repoRoot: 'C:/Projects/Bolt', dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt', env: {}, exists: () => false }),
      readiness,
      health,
      spawn,
    });

    const status = await supervisor.ensureStarted();

    expect(spawn).toHaveBeenCalledOnce();
    expect(health).not.toHaveBeenCalled();
    expect(status.status).toBe('down');
    expect(child.kill).toHaveBeenCalled();
    expect(supervisor.getVerifiedGeneration()).toBeNull();
  });

  it('rebuilds a minimal child environment without inherited Bolt secrets or Python injection', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {
        SystemRoot: 'C:/Windows',
        WINDIR: 'C:/Windows',
        TEMP: 'C:/Temp',
        TMP: 'C:/Temp',
        PATH: 'C:/attacker/bin',
        PYTHONPATH: 'C:/attacker/python',
        PYTHONHOME: 'C:/attacker/home',
        BOLT_AGENT_CORE_TOKEN: 'old-token',
        BOLT_AGENT_CORE_PORT: '8765',
        BOLT_CORE_BOOTSTRAP_KEY: 'old-bootstrap',
        BOLT_CORE_BEARER: 'old-bearer',
        BOLT_EXECUTION_AUDIT_PATH: 'C:/attacker/audit.json',
        PROVIDER_API_KEY: 'provider-secret',
      },
      exists: () => false,
      generationFactory: () => ({
        startupId: 'new-startup',
        bootstrapKey: 'new-bootstrap',
        bearerToken: 'new-bearer',
      }),
    });

    expect(runtime.env).toEqual({
      SystemRoot: 'C:/Windows',
      WINDIR: 'C:/Windows',
      TEMP: 'C:/Temp',
      TMP: 'C:/Temp',
      PATH: '',
      PYTHONPATH: 'C:/Projects/Bolt/services/agent-core/src',
      BOLT_CORE_STARTUP_ID: 'new-startup',
      BOLT_CORE_BOOTSTRAP_KEY: 'new-bootstrap',
      BOLT_CORE_BEARER: 'new-bearer',
      BOLT_WORKSPACE: 'C:/Projects/Bolt',
      BOLT_CORE_DATA_ROOT: 'C:/Users/bolt/AppData/Roaming/Bolt',
      BOLT_CORE_PROTOCOL_VERSION: '1',
    });
    expect(Object.values(runtime.env)).not.toContain('old-token');
    expect(Object.values(runtime.env)).not.toContain('8765');
    expect(Object.values(runtime.env)).not.toContain('old-bootstrap');
    expect(Object.values(runtime.env)).not.toContain('old-bearer');
    expect(Object.values(runtime.env)).not.toContain('provider-secret');
    expect(runtime.baseUrl).toBe('http://127.0.0.1:0');
  });

  it('resolves the development desktop runner from the repo workspace', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {},
      exists: (path) => path.endsWith('services/agent-core/.venv/Scripts/python.exe')
    });

    expect(runtime.baseUrl).toBe('http://127.0.0.1:0');
    expect(runtime.command).toBe('C:/Projects/Bolt/services/agent-core/.venv/Scripts/python.exe');
    expect(runtime.args).toEqual(['-m', 'bolt_core.desktop_runner']);
    expect(runtime.env.PYTHONPATH).toBe('C:/Projects/Bolt/services/agent-core/src');
  });

  it('ignores inherited development runtime overrides', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      env: {
        BOLT_AGENT_CORE_PORT: '8765',
        BOLT_AGENT_CORE_PYTHON: 'C:/Python/python.exe',
        PYTHONPATH: 'C:/existing'
      },
      exists: () => false
    });

    expect(runtime.baseUrl).toBe('http://127.0.0.1:0');
    expect(runtime.command).toBe('python');
    expect(runtime.args).toEqual(['-m', 'bolt_core.desktop_runner']);
    expect(runtime.env.PYTHONPATH).toBe('C:/Projects/Bolt/services/agent-core/src');
  });

  it('does not adopt a healthy endpoint without an authenticated readiness proof', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean; pid: number };
    child.kill = vi.fn();
    child.killed = false;
    child.pid = 1234;
    const spawn = vi.fn().mockReturnValue(child);
    const supervisor = new AgentCoreSupervisor({
      runtime: resolveAgentCoreRuntime({ repoRoot: 'C:/Projects/Bolt', dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt', env: {}, exists: () => false }),
      health: vi.fn().mockResolvedValue(true),
      readiness: vi.fn().mockRejectedValue(new Error('CORE_READINESS_INVALID')),
      spawn
    });

    const status = await supervisor.ensureStarted();

    expect(status.status).toBe('down');
    expect(spawn).toHaveBeenCalledOnce();
    expect(child.kill).toHaveBeenCalled();
  });

  it('spawns agent core when health is down', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean };
    child.kill = vi.fn();
    child.killed = false;
    const spawn = vi.fn().mockReturnValue(child);
    const health = vi.fn().mockResolvedValue(true);
    const runtime = resolveAgentCoreRuntime({ repoRoot: 'C:/Projects/Bolt', dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt', env: {}, exists: () => false });
    const readiness = vi.fn().mockResolvedValue({
      generationId: runtime.startupId,
      endpoint: 'http://127.0.0.1:43123',
      port: 43123,
    });
    const supervisor = new AgentCoreSupervisor({ runtime, health, readiness, spawn });

    const status = await supervisor.ensureStarted();
    supervisor.stop();

    expect(status.status).toBe('ok');
    expect(status.started).toBe(true);
    expect(spawn).toHaveBeenCalledWith(runtime.command, runtime.args, expect.objectContaining({ cwd: runtime.cwd, env: runtime.env }));
    expect(child.kill).toHaveBeenCalled();
  });

  it('fails closed in packaged mode when bundled agent core resources are missing', async () => {
    const spawn = vi.fn();
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      resourcesPath: 'C:/Program Files/Bolt/resources',
      packaged: true,
      env: {},
      exists: () => false
    });
    const supervisor = new AgentCoreSupervisor({
      runtime,
      health: vi.fn().mockResolvedValue(false),
      spawn
    });

    const status = await supervisor.ensureStarted();

    expect(runtime.cwd).toBe('C:/Program Files/Bolt/resources/agent-core');
    expect(runtime.env.PYTHONPATH).toContain('C:/Program Files/Bolt/resources/agent-core/src');
    expect(status.status).toBe('down');
    expect(status.started).toBe(false);
    expect(status.error).toContain('missing packaged Agent Core resource');
    expect(spawn).not.toHaveBeenCalled();
  });

  it('ignores agent core path and python overrides in packaged mode', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      dataRoot: 'C:/Users/bolt/AppData/Roaming/Bolt',
      resourcesPath: 'C:/Program Files/Bolt/resources',
      packaged: true,
      env: {
        BOLT_AGENT_CORE_ROOT: 'C:/attacker/core',
        BOLT_AGENT_CORE_SRC: 'C:/attacker/src',
        BOLT_AGENT_CORE_PYTHON: 'C:/attacker/python.exe',
        PYTHONPATH: 'C:/existing'
      },
      exists: () => true
    });

    expect(runtime.cwd).toBe('C:/Program Files/Bolt/resources/agent-core');
    expect(runtime.command).toBe('C:/Program Files/Bolt/resources/agent-core/.venv/Scripts/python.exe');
    expect(runtime.env.PYTHONPATH).toBe('C:/Program Files/Bolt/resources/agent-core/src');
  });
});
