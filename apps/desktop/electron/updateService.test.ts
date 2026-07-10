import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import {
  UpdateService,
  assertHttpsAllowedUrl,
  compareSemver,
  signManifest,
  type UpdateManifest,
} from './updateService';

const secret = Buffer.from('test-trust-secret');
const allowedHosts = ['updates.bolt.local'];

function manifestFor(version: string, body: Buffer): UpdateManifest {
  const artifact = {
    url: 'https://updates.bolt.local/Bolt-Setup.exe',
    sha256: createHash('sha256').update(body).digest('hex'),
    size: body.byteLength,
  };
  const unsigned = {
    version,
    channel: 'beta',
    min_version: '0.1.0',
    artifacts: [artifact],
  };
  return { ...unsigned, signature: signManifest(unsigned, secret) };
}

describe('UpdateService', () => {
  it('rejects non-https and non-allowlisted hosts', () => {
    expect(() => assertHttpsAllowedUrl('http://updates.bolt.local/m.json', allowedHosts)).toThrow(/https_required/);
    expect(() => assertHttpsAllowedUrl('https://evil.example/m.json', allowedHosts)).toThrow(/host_not_allowlisted/);
  });

  it('compareSemver orders versions', () => {
    expect(compareSemver('0.2.0', '0.1.9')).toBe(1);
    expect(compareSemver('0.1.0', '0.1.0')).toBe(0);
  });

  it('blocks production channel until explicitly enabled', async () => {
    const service = new UpdateService({
      currentVersion: '0.1.0',
      allowedHosts,
      trustSecret: secret,
      fetchManifest: async () => {
        throw new Error('should not fetch');
      },
      productionChannelEnabled: false,
    });
    await expect(service.checkForUpdate('https://updates.bolt.local/manifest.json')).resolves.toMatchObject({
      status: 'rejected',
      reason: 'production_update_channel_blocked',
    });
  });

  it('rejects tampered manifest signatures', async () => {
    const body = Buffer.from('installer');
    const good = manifestFor('0.2.0', body);
    const bad = { ...good, signature: '00'.repeat(32) };
    const service = new UpdateService({
      currentVersion: '0.1.0',
      allowedHosts,
      trustSecret: secret,
      fetchManifest: async () => bad,
      productionChannelEnabled: true,
    });
    await expect(service.checkForUpdate('https://updates.bolt.local/manifest.json')).resolves.toMatchObject({
      status: 'rejected',
      checkId: 'update.reject-tamper',
    });
  });

  it('accepts signed newer manifest and verifies artifact hash', async () => {
    const body = Buffer.from('installer-bytes');
    const good = manifestFor('0.2.0', body);
    const service = new UpdateService({
      currentVersion: '0.1.0',
      allowedHosts,
      trustSecret: secret,
      fetchManifest: async () => good,
      downloadArtifact: async () => body,
      productionChannelEnabled: true,
    });
    const decision = await service.checkForUpdate('https://updates.bolt.local/manifest.json');
    expect(decision.status).toBe('available');
    if (decision.status !== 'available') throw new Error('expected available');
    await expect(service.downloadAndVerify(decision.artifact)).resolves.toMatchObject({ status: 'verified' });
  });

  it('rejects hash mismatch and keeps rollback semantics on install failure', async () => {
    const body = Buffer.from('installer-bytes');
    const good = manifestFor('0.2.0', body);
    const service = new UpdateService({
      currentVersion: '0.1.0',
      allowedHosts,
      trustSecret: secret,
      fetchManifest: async () => good,
      downloadArtifact: async () => Buffer.from('installer-TAMPR'),
      productionChannelEnabled: true,
      coreBusy: () => false,
    });
    const decision = await service.checkForUpdate('https://updates.bolt.local/manifest.json');
    if (decision.status !== 'available') throw new Error('expected available');
    await expect(service.downloadAndVerify(decision.artifact)).resolves.toMatchObject({
      status: 'rejected',
      reason: 'hash_mismatch',
    });
    expect(service.evaluateInstallOutcome(false)).toMatchObject({
      checkId: 'update.rollback',
      reason: 'install_failed_keep_current',
    });
  });

  it('defers update while core is busy', async () => {
    const body = Buffer.from('installer-bytes');
    const good = manifestFor('0.2.0', body);
    const service = new UpdateService({
      currentVersion: '0.1.0',
      allowedHosts,
      trustSecret: secret,
      fetchManifest: async () => good,
      downloadArtifact: async () => body,
      productionChannelEnabled: true,
      coreBusy: () => true,
    });
    const decision = await service.checkForUpdate('https://updates.bolt.local/manifest.json');
    if (decision.status !== 'available') throw new Error('expected available');
    await expect(service.downloadAndVerify(decision.artifact)).resolves.toMatchObject({
      status: 'rejected',
      reason: 'core_busy',
    });
  });
});
