import { spawn as nodeSpawn, type ChildProcess } from 'node:child_process';
import path from 'node:path';

export interface AgentCoreRuntimeOptions {
  repoRoot: string;
  resourcesPath?: string;
  packaged?: boolean;
  env?: NodeJS.ProcessEnv;
  exists?: (path: string) => boolean;
}

export interface AgentCoreRuntime {
  baseUrl: string;
  command: string;
  args: string[];
  cwd: string;
  env: NodeJS.ProcessEnv;
}

export interface AgentCoreStatus {
  status: 'ok' | 'down';
  started: boolean;
  baseUrl: string;
  error?: string;
}

type HealthCheck = (baseUrl: string) => Promise<boolean>;
type SpawnProcess = (command: string, args: string[], options: { cwd: string; env: NodeJS.ProcessEnv; windowsHide: boolean }) => ChildProcess;

export function resolveAgentCoreRuntime(options: AgentCoreRuntimeOptions): AgentCoreRuntime {
  const env = options.env ?? process.env;
  const port = normalizePort(env.BOLT_AGENT_CORE_PORT);
  const coreRoot = env.BOLT_AGENT_CORE_ROOT || defaultCoreRoot(options);
  const sourceRoot = env.BOLT_AGENT_CORE_SRC || joinPath(coreRoot, 'src');
  const venvPython = joinPath(coreRoot, '.venv', 'Scripts', 'python.exe');
  const command = env.BOLT_AGENT_CORE_PYTHON || ((options.exists ?? (() => false))(venvPython) ? venvPython : 'python');
  return {
    baseUrl: `http://127.0.0.1:${port}`,
    command,
    args: ['-m', 'uvicorn', 'bolt_core.app:create_app', '--factory', '--host', '127.0.0.1', '--port', String(port)],
    cwd: coreRoot,
    env: { ...env, PYTHONPATH: prependPath(sourceRoot, env.PYTHONPATH) }
  };
}

export class AgentCoreSupervisor {
  private child: ChildProcess | null = null;
  private readonly runtime: AgentCoreRuntime;
  private readonly health: HealthCheck;
  private readonly spawn: SpawnProcess;

  constructor(options: { runtime: AgentCoreRuntime; health?: HealthCheck; spawn?: SpawnProcess }) {
    this.runtime = options.runtime;
    this.health = options.health ?? defaultHealthCheck;
    this.spawn = options.spawn ?? nodeSpawn;
  }

  async ensureStarted(): Promise<AgentCoreStatus> {
    if (await this.health(this.runtime.baseUrl)) return { status: 'ok', started: false, baseUrl: this.runtime.baseUrl };
    if (!this.child || this.child.killed) {
      this.child = this.spawn(this.runtime.command, this.runtime.args, { cwd: this.runtime.cwd, env: this.runtime.env, windowsHide: true });
    }
    for (let attempt = 0; attempt < 20; attempt++) {
      if (await this.health(this.runtime.baseUrl)) return { status: 'ok', started: true, baseUrl: this.runtime.baseUrl };
      await delay(250);
    }
    return { status: 'down', started: true, baseUrl: this.runtime.baseUrl, error: 'Agent Core did not become healthy' };
  }

  stop(): void {
    if (this.child && !this.child.killed) this.child.kill();
    this.child = null;
  }
}

export async function defaultHealthCheck(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/health`);
    const payload = await response.json() as { status?: string };
    return payload.status === 'ok';
  } catch {
    return false;
  }
}

function defaultCoreRoot(options: AgentCoreRuntimeOptions): string {
  if (options.packaged && options.resourcesPath) return joinPath(options.resourcesPath, 'agent-core');
  return joinPath(options.repoRoot, 'services', 'agent-core');
}

function normalizePort(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 && parsed < 65536 ? parsed : 8000;
}

function prependPath(first: string, rest: string | undefined): string {
  return rest ? `${first}${path.delimiter}${rest}` : first;
}

function joinPath(root: string, ...parts: string[]): string {
  const separator = root.includes('/') ? '/' : path.sep;
  return [root.replace(/[\\/]$/, ''), ...parts].join(separator);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
