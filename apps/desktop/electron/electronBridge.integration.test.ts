// @vitest-environment node
import { spawn, execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';
import { describe, expect, it, beforeAll } from 'vitest';

const require = createRequire(import.meta.url);
const electron = join(dirname(require.resolve('electron')), 'dist', 'electron.exe');
const fixture = join(__dirname, 'fixtures', 'bridge-integration.cjs');

async function runFixtureOnce(): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    const child = spawn(electron, [fixture], {
      env: {
        ...process.env,
        ELECTRON_RUN_AS_NODE: undefined,
        ELECTRON_NO_ATTACH_CONSOLE: '1',
      },
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    const killer = setTimeout(() => {
      stderr += 'parent-watchdog-timeout';
      child.kill('SIGTERM');
      setTimeout(() => child.kill('SIGKILL'), 1000).unref?.();
    }, 15000);
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.once('error', (error) => {
      clearTimeout(killer);
      reject(error);
    });
    child.once('exit', (code) => {
      clearTimeout(killer);
      if (code === 0 && stdout.trim()) resolve(stdout);
      else reject(new Error(stderr || `electron exited ${code}`));
    });
  });
}

describe('real Electron contextIsolation bridge', () => {
  beforeAll(() => {
    const tsc = join(__dirname, '..', 'node_modules', 'typescript', 'bin', 'tsc');
    execFileSync(process.execPath, [tsc, '-p', 'tsconfig.electron.json'], {
      cwd: join(__dirname, '..'),
      stdio: 'pipe',
      windowsHide: true,
    });
  }, 60000);

  it('returns a synchronous handle, resolves DTO promise, and cancels across contextBridge', async () => {
    let output = '';
    try {
      output = await runFixtureOnce();
    } catch {
      output = await runFixtureOnce();
    }
    const linesOut = output.trim().split(String.fromCharCode(10)).map((line) => line.replace(new RegExp(String.fromCharCode(13) + '$'), '')).filter(Boolean);
    const result = JSON.parse(linesOut[linesOut.length - 1] ?? '{}');
    expect(result).toMatchObject({
      synchronousHandle: true,
      promiseResponse: true,
      cancelResult: 'cancelled',
      contextIsolated: true,
      noEndpoint: true,
      noRawIpc: true,
      hasDiagnostics: true,
      hasUpdate: true,
    });
  }, 40000);
});
