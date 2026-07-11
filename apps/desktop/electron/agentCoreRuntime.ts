import { spawn as nodeSpawn, type ChildProcess } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import type { VerifiedReadiness } from './agentCoreReadiness.js';
import { waitForReadinessProof } from './agentCoreReadiness.js';

export interface AgentCoreRuntimeOptions {
  repoRoot: string;
  dataRoot?: string;
  resourcesPath?: string;
  packaged?: boolean;
  env?: NodeJS.ProcessEnv;
  exists?: (path: string) => boolean;
  generationFactory?: () => AgentCoreGenerationSecrets;
}

export interface AgentCoreGenerationSecrets {
  startupId: string;
  bootstrapKey: string;
  bearerToken: string;
}

export interface AgentCoreRuntime {
  baseUrl: string;
  command: string;
  args: string[];
  cwd: string;
  env: NodeJS.ProcessEnv;
  authToken: string;
  startupId: string;
  bootstrapKey: string;
  validationError?: string;
}

export interface AgentCoreStatus {
  status: 'ok' | 'down';
  started: boolean;
  baseUrl: string;
  error?: string;
}

type HealthCheck = (baseUrl: string) => Promise<boolean>;
type ReadinessCheck = (child: ChildProcess, runtime: AgentCoreRuntime) => Promise<VerifiedReadiness>;
type SpawnProcess = (command: string, args: string[], options: { cwd: string; env: NodeJS.ProcessEnv; windowsHide: boolean }) => ChildProcess;

export function resolveAgentCoreRuntime(options: AgentCoreRuntimeOptions): AgentCoreRuntime {
  const env = options.env ?? process.env;
  const port = 0;
  const coreRoot = options.packaged ? defaultCoreRoot(options) : defaultCoreRoot(options);
  const sourceRoot = joinPath(coreRoot, 'src');
  const venvPython = joinPath(coreRoot, '.venv', 'Scripts', 'python.exe');
  const command = venvPython && (options.exists ?? (() => false))(venvPython) ? venvPython : 'python';
  const validationError = options.dataRoot
    ? packagedResourceError(options, coreRoot, sourceRoot)
    : 'Agent Core data root is required';
  const generation = (options.generationFactory ?? createGenerationSecrets)();
  return {
    baseUrl: `http://127.0.0.1:${port}`,
    command,
    args: ['-m', 'bolt_core.desktop_runner'],
    cwd: coreRoot,
    env: buildChildEnvironment(env, sourceRoot, options.repoRoot, options.dataRoot, generation),
    authToken: generation.bearerToken,
    startupId: generation.startupId,
    bootstrapKey: generation.bootstrapKey,
    validationError
  };
}

export class AgentCoreSupervisor {
  private child: ChildProcess | null = null;
  private runtime: AgentCoreRuntime | null = null;
  private readonly runtimeFactory: () => AgentCoreRuntime;
  private readonly health: HealthCheck;
  private readonly readiness: ReadinessCheck;
  private readonly spawn: SpawnProcess;
  private verified: { generationId: string; endpoint: string; bearerToken: string } | null = null;

  constructor(options: { runtime?: AgentCoreRuntime; runtimeFactory?: () => AgentCoreRuntime; health?: HealthCheck; readiness?: ReadinessCheck; spawn?: SpawnProcess }) {
    if (!options.runtime && !options.runtimeFactory) throw new Error('Agent Core runtime is required');
    this.runtimeFactory = options.runtimeFactory ?? (() => options.runtime as AgentCoreRuntime);
    this.health = options.health ?? defaultHealthCheck;
    this.readiness = options.readiness ?? defaultReadiness;
    this.spawn = options.spawn ?? nodeSpawn;
  }

  async ensureStarted(): Promise<AgentCoreStatus> {
    const runtime = this.runtime ?? this.runtimeFactory();
    if (runtime.validationError) {
      this.runtime = null;
      return { status: 'down', started: false, baseUrl: runtime.baseUrl, error: runtime.validationError };
    }
    try {
      if (!this.child || this.child.killed) {
        this.runtime = runtime;
        this.child = this.spawn(runtime.command, runtime.args, { cwd: runtime.cwd, env: runtime.env, windowsHide: true });
        const startedChild = this.child;
        startedChild.once('exit', () => {
          if (this.child === startedChild) this.revoke();
        });
        startedChild.once('error', () => {
          if (this.child === startedChild) this.revoke();
        });
      }
      const readiness = await this.readiness(this.child, runtime);
      if (!await this.health(readiness.endpoint)) throw new Error('Agent Core did not become healthy');
      this.verified = {
        generationId: readiness.generationId,
        endpoint: readiness.endpoint,
        bearerToken: runtime.authToken,
      };
      return { status: 'ok', started: true, baseUrl: readiness.endpoint };
    } catch (error) {
      this.revoke();
      return {
        status: 'down',
        started: true,
        baseUrl: runtime.baseUrl,
        error: error instanceof Error ? error.message : 'Agent Core startup failed',
      };
    }
  }

  getVerifiedGeneration(): { generationId: string; endpoint: string; bearerToken: string } | null {
    return this.verified;
  }

  stop(): void {
    this.revoke();
  }

  private revoke(): void {
    this.verified = null;
    if (this.child && !this.child.killed) this.child.kill();
    this.child = null;
    this.runtime = null;
  }
}

export async function defaultHealthCheck(baseUrl: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5_000);
    try {
      const response = await fetch(`${baseUrl}/health`, {
        redirect: 'error',
        signal: controller.signal,
      });
      if (response.status !== 200) return false;
      const raw = await response.text();
      const body = raw.trim();
      if (raw.length > 4096) return false;
      if (body.length < 2) return false;
      // Reject BOM, NUL, and duplicate JSON keys.
      if (raw.codePointAt(0) === 0xfeff || raw.includes('\u0000')) return false;
      if (body.includes('\\')) return false;
      try {
        const seen = new Set<string>();
        for (const match of body.matchAll(/(?:\{|,)\s*"([^"]+)"\s*:/g)) {
          if (seen.has(match[1])) return false;
          seen.add(match[1]);
        }
        const payload = JSON.parse(raw) as Record<string, unknown>;
        if (Object.keys(payload).sort().join(',') !== 'service,status') return false;
        if (payload.status !== 'ok' || payload.service !== 'bolt-agent-core') return false;
      } catch {
        return false;
      }
      return true;
    } finally {
      clearTimeout(timeout);
    }
  } catch {
    return false;
  }
}

function buildChildEnvironment(
  parent: NodeJS.ProcessEnv,
  sourceRoot: string,
  workspace: string,
  dataRoot: string | undefined,
  generation: AgentCoreGenerationSecrets,
): NodeJS.ProcessEnv {
  const child: NodeJS.ProcessEnv = {};
  for (const name of [
    'SystemRoot',
    'WINDIR',
    'ComSpec',
    'TEMP',
    'TMP',
    'PATHEXT',
    'PROCESSOR_ARCHITECTURE',
    'NUMBER_OF_PROCESSORS',
    'USERPROFILE',
    'APPDATA',
    'LOCALAPPDATA',
  ]) {
    if (parent[name] !== undefined) child[name] = parent[name];
  }
  child.PATH = '';
  child.PYTHONPATH = sourceRoot;
  child.BOLT_CORE_STARTUP_ID = generation.startupId;
  child.BOLT_CORE_BOOTSTRAP_KEY = generation.bootstrapKey;
  child.BOLT_CORE_BEARER = generation.bearerToken;
  child.BOLT_WORKSPACE = workspace;
  if (dataRoot) child.BOLT_CORE_DATA_ROOT = dataRoot;
  child.BOLT_CORE_PROTOCOL_VERSION = '1';
  return child;
}

function createGenerationSecrets(): AgentCoreGenerationSecrets {
  return {
    startupId: randomBytes(32).toString('base64url'),
    bootstrapKey: randomBytes(32).toString('base64url'),
    bearerToken: randomBytes(32).toString('base64url'),
  };
}

function defaultCoreRoot(options: AgentCoreRuntimeOptions): string {
  if (options.packaged && options.resourcesPath) return joinPath(options.resourcesPath, 'agent-core');
  return joinPath(options.repoRoot, 'services', 'agent-core');
}

function packagedResourceError(options: AgentCoreRuntimeOptions, coreRoot: string, sourceRoot: string): string | undefined {
  if (!options.packaged) return undefined;
  const exists = options.exists ?? (() => false);
  const missing = [
    joinPath(sourceRoot, 'bolt_core', 'app.py'),
    joinPath(coreRoot, 'pyproject.toml'),
    joinPath(coreRoot, '.venv', 'Scripts', 'python.exe'),
  ].filter((file) => !exists(file));
  if (missing.length === 0) return undefined;
  return `missing packaged Agent Core resource: ${missing.join(', ')}`;
}

function joinPath(root: string, ...parts: string[]): string {
  const separator = root.includes('/') ? '/' : path.sep;
  return [root.replace(/[\\/]$/, ''), ...parts].join(separator);
}

async function defaultReadiness(child: ChildProcess, runtime: AgentCoreRuntime): Promise<VerifiedReadiness> {
  if (!child.pid) throw new Error('CORE_READINESS_INVALID');
  return waitForReadinessProof(child, {
    startupId: runtime.startupId,
    bootstrapKey: Buffer.from(runtime.bootstrapKey, 'base64url'),
    childPid: child.pid,
    timeoutMs: 5_000,
  });
}
