import { createHmac, timingSafeEqual } from 'node:crypto';
import type { ChildProcess } from 'node:child_process';

const FIELDS = ['type', 'version', 'startup_id', 'pid', 'host', 'port', 'proof'].sort();
const DUPLICATE_KEY = /(?:^|,)\s*"([^"]+)"\s*:/g;

export type VerifiedReadiness = {
  generationId: string;
  endpoint: string;
  port: number;
};

export function waitForReadinessProof(
  child: ChildProcess,
  expected: { startupId: string; bootstrapKey: Buffer; childPid: number; timeoutMs: number },
): Promise<VerifiedReadiness> {
  return new Promise((resolve, reject) => {
    if (!child.stdout) return reject(new Error('CORE_READINESS_INVALID'));
    let buffer = Buffer.alloc(0);
    let settled = false;
    const timer = setTimeout(() => finish(new Error('CORE_READINESS_TIMEOUT')), expected.timeoutMs);
    const finish = (error?: Error, value?: VerifiedReadiness) => {
      if (settled) {
        if (error) child.stdout?.emit('error', error);
        return;
      }
      settled = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve(value!);
    };
    child.stdout.on('data', (chunk: Buffer | string) => {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      if (settled) return finish(new Error('CORE_READINESS_INVALID'));
      buffer = Buffer.concat([buffer, bytes]);
      if (buffer.length > 768) return finish(new Error('CORE_READINESS_INVALID'));
      const newline = buffer.indexOf(0x0a);
      if (newline === -1) return;
      if (newline !== buffer.length - 1) return finish(new Error('CORE_READINESS_INVALID'));
      try {
        finish(undefined, verifyReadinessProof(buffer, expected));
      } catch (error) {
        finish(error instanceof Error ? error : new Error('CORE_READINESS_INVALID'));
      }
    });
  });
}

export function verifyReadinessProof(
  input: Buffer,
  expected: { startupId: string; bootstrapKey: Buffer; childPid: number },
): VerifiedReadiness {
  try {
    if (input.length > 768 || input.length < 2 || input.at(-1) !== 0x0a || input.subarray(0, -1).includes(0x0a)) fail();
    if (input.includes(0) || input.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) fail();
    const source = new TextDecoder('utf-8', { fatal: true }).decode(input.subarray(0, -1));
    rejectDuplicateKeys(source);
    const payload = JSON.parse(source) as Record<string, unknown>;
    if (!isPlainRecord(payload) || JSON.stringify(Object.keys(payload).sort()) !== JSON.stringify(FIELDS)) fail();
    if (payload.type !== 'bolt.core.ready' || payload.version !== 1) fail();
    if (payload.startup_id !== expected.startupId || payload.pid !== expected.childPid || payload.host !== '127.0.0.1') fail();
    if (!Number.isInteger(payload.port) || (payload.port as number) < 1 || (payload.port as number) > 65535) fail();
    if (typeof payload.proof !== 'string') fail();
    const suppliedProof = decodeCanonical(payload.proof, 32);
    decodeCanonical(expected.startupId, 32);
    const transcript = `bolt-core-ready-v1\n${expected.startupId}\n${expected.childPid}\n127.0.0.1\n${payload.port}\n`;
    const expectedProof = createHmac('sha256', expected.bootstrapKey).update(transcript).digest();
    if (!timingSafeEqual(suppliedProof, expectedProof)) fail();
    return {
      generationId: expected.startupId,
      endpoint: `http://127.0.0.1:${payload.port}`,
      port: payload.port as number,
    };
  } catch (error) {
    if (error instanceof Error && error.message === 'CORE_READINESS_INVALID') throw error;
    fail();
  }
}

function rejectDuplicateKeys(source: string): void {
  const seen = new Set<string>();
  for (const match of source.matchAll(DUPLICATE_KEY)) {
    if (seen.has(match[1])) fail();
    seen.add(match[1]);
  }
}

function decodeCanonical(value: string, length: number): Buffer {
  if (!/^[A-Za-z0-9_-]+$/.test(value) || value.includes('=')) fail();
  const decoded = Buffer.from(value, 'base64url');
  if (decoded.length !== length || decoded.toString('base64url') !== value) fail();
  return decoded;
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

function fail(): never {
  throw new Error('CORE_READINESS_INVALID');
}
