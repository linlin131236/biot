// @vitest-environment node
import { createHmac } from 'node:crypto';
import { PassThrough } from 'node:stream';
import { describe, expect, it } from 'vitest';
import { verifyReadinessProof, waitForReadinessProof } from './agentCoreReadiness';

const startupId = Buffer.alloc(32, 0x73).toString('base64url');
const bootstrapKey = Buffer.alloc(32, 0x6b);

function line(overrides: Record<string, unknown> = {}): Buffer {
  const pid = Number(overrides.pid ?? 1234);
  const host = String(overrides.host ?? '127.0.0.1');
  const port = Number(overrides.port ?? 43123);
  const candidateStartupId = String(overrides.startup_id ?? startupId);
  const transcript = `bolt-core-ready-v1\n${candidateStartupId}\n${pid}\n${host}\n${port}\n`;
  const payload = {
    type: 'bolt.core.ready',
    version: 1,
    startup_id: candidateStartupId,
    pid,
    host,
    port,
    proof: createHmac('sha256', bootstrapKey).update(transcript).digest('base64url'),
    ...overrides,
  };
  return Buffer.from(`${JSON.stringify(payload)}\n`, 'utf8');
}

describe('Agent Core readiness proof', () => {
  it('consumes one stdout proof and rejects any later stdout byte', async () => {
    const stdout = new PassThrough();
    const child = { stdout, once: () => child } as unknown as import('node:child_process').ChildProcess;
    const verified = waitForReadinessProof(child, {
      startupId,
      bootstrapKey,
      childPid: 1234,
      timeoutMs: 1000,
    });

    stdout.write(line());
    await expect(verified).resolves.toEqual({
      generationId: startupId,
      endpoint: 'http://127.0.0.1:43123',
      port: 43123,
    });

    const violation = new Promise<Error>((resolve) => {
      stdout.once('error', resolve);
    });
    stdout.write(Buffer.from('second line\n'));
    await expect(violation).resolves.toMatchObject({ message: 'CORE_READINESS_INVALID' });
  });

  it('times out if the child emits no complete proof', async () => {
    const stdout = new PassThrough();
    const child = { stdout, once: () => child } as unknown as import('node:child_process').ChildProcess;

    await expect(waitForReadinessProof(child, {
      startupId,
      bootstrapKey,
      childPid: 1234,
      timeoutMs: 10,
    })).rejects.toThrow('CORE_READINESS_TIMEOUT');
  });

  it('verifies the exact startup identity, child pid, loopback host, port, and HMAC', () => {
    expect(verifyReadinessProof(line(), { startupId, bootstrapKey, childPid: 1234 })).toEqual({
      generationId: startupId,
      endpoint: 'http://127.0.0.1:43123',
      port: 43123,
    });
  });

  it.each([
    ['startup ID', { startup_id: Buffer.alloc(32, 0x78).toString('base64url') }],
    ['pid', { pid: 9999 }],
    ['host', { host: 'localhost' }],
    ['version', { version: 2 }],
    ['HMAC', { proof: Buffer.alloc(32).toString('base64url') }],
    ['extra field', { extra: true }],
  ])('rejects mismatched %s', (_label, overrides) => {
    expect(() => verifyReadinessProof(line(overrides), { startupId, bootstrapKey, childPid: 1234 }))
      .toThrow('CORE_READINESS_INVALID');
  });

  it.each([
    Buffer.from('{}', 'utf8'),
    Buffer.from('{}\n{}\n', 'utf8'),
    Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), line()]),
    Buffer.concat([line().subarray(0, 10), Buffer.from([0]), line().subarray(10)]),
    Buffer.alloc(769, 0x20),
    Buffer.from('{"type":"bolt.core.ready","type":"duplicate"}\n', 'utf8'),
  ])('rejects malformed framing and JSON', (input) => {
    expect(() => verifyReadinessProof(input, { startupId, bootstrapKey, childPid: 1234 }))
      .toThrow('CORE_READINESS_INVALID');
  });
});
