// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { resolveAgentCoreRuntime, AgentCoreSupervisor } from './agentCoreRuntime';

describe('agent core runtime', () => {
  it('resolves the development uvicorn command from the repo workspace', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: {},
      exists: (path) => path.endsWith('services/agent-core/.venv/Scripts/python.exe')
    });

    expect(runtime.baseUrl).toBe('http://127.0.0.1:8000');
    expect(runtime.command).toBe('C:/Projects/Bolt/services/agent-core/.venv/Scripts/python.exe');
    expect(runtime.args).toEqual(['-m', 'uvicorn', 'bolt_core.app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000']);
    expect(runtime.env.PYTHONPATH).toContain('C:/Projects/Bolt/services/agent-core/src');
  });

  it('honors explicit runtime environment overrides', () => {
    const runtime = resolveAgentCoreRuntime({
      repoRoot: 'C:/Projects/Bolt',
      env: {
        BOLT_AGENT_CORE_PORT: '8765',
        BOLT_AGENT_CORE_PYTHON: 'C:/Python/python.exe',
        PYTHONPATH: 'C:/existing'
      },
      exists: () => false
    });

    expect(runtime.baseUrl).toBe('http://127.0.0.1:8765');
    expect(runtime.command).toBe('C:/Python/python.exe');
    expect(runtime.args.at(-1)).toBe('8765');
    expect(runtime.env.PYTHONPATH).toBe('C:/Projects/Bolt/services/agent-core/src;C:/existing');
  });

  it('does not spawn agent core when health already passes', async () => {
    const spawn = vi.fn();
    const supervisor = new AgentCoreSupervisor({
      runtime: resolveAgentCoreRuntime({ repoRoot: 'C:/Projects/Bolt', env: {}, exists: () => false }),
      health: vi.fn().mockResolvedValue(true),
      spawn
    });

    const status = await supervisor.ensureStarted();

    expect(status.status).toBe('ok');
    expect(status.started).toBe(false);
    expect(spawn).not.toHaveBeenCalled();
  });

  it('spawns agent core when health is down', async () => {
    const child = new EventEmitter() as EventEmitter & { kill: ReturnType<typeof vi.fn>; killed: boolean };
    child.kill = vi.fn();
    child.killed = false;
    const spawn = vi.fn().mockReturnValue(child);
    const health = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const runtime = resolveAgentCoreRuntime({ repoRoot: 'C:/Projects/Bolt', env: {}, exists: () => false });
    const supervisor = new AgentCoreSupervisor({ runtime, health, spawn });

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
    expect(runtime.env.PYTHONPATH).toBe('C:/Program Files/Bolt/resources/agent-core/src;C:/existing');
  });
});
