// @vitest-environment node
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';
import { describe, expect, it } from 'vitest';

const require = createRequire(import.meta.url);
const electron = join(dirname(require.resolve('electron')), 'dist', 'electron.exe');
const fixture = join(__dirname, 'fixtures', 'bridge-integration.cjs');

describe('real Electron contextIsolation bridge', () => {
  it('returns a synchronous handle, resolves DTO promise, and cancels across contextBridge', async () => {
    const output = await new Promise<string>((resolve, reject) => {
      const child = spawn(electron, [fixture], {
        env: { ...process.env, ELECTRON_RUN_AS_NODE: undefined },
        windowsHide: true,
      });
      let stdout = '';
      let stderr = '';
      child.stdout.on('data', (chunk) => { stdout += chunk; });
      child.stderr.on('data', (chunk) => { stderr += chunk; });
      child.once('error', reject);
      child.once('exit', (code) => code === 0 ? resolve(stdout) : reject(new Error(stderr || `electron exited ${code}`)));
    });

    const result = JSON.parse(output.trim());
    expect(result).toEqual({
      synchronousHandle: true,
      promiseResponse: true,
      cancelResult: 'cancelled',
      contextIsolated: true,
      noEndpoint: true,
      noRawIpc: true,
    });
  }, 20_000);
});
