import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

export type UpdateArtifact = {
  url: string;
  sha256: string;
  size: number;
};

export type UpdateManifest = {
  version: string;
  channel: string;
  min_version: string;
  artifacts: UpdateArtifact[];
  signature: string;
};

export type UpdateDecision =
  | { status: 'up_to_date' }
  | { status: 'available'; version: string; artifact: UpdateArtifact }
  | { status: 'rejected'; reason: string; checkId: string };

export type UpdateServiceOptions = {
  currentVersion: string;
  allowedHosts: string[];
  trustSecret: Buffer;
  fetchManifest: (url: string) => Promise<UpdateManifest>;
  downloadArtifact?: (url: string) => Promise<Buffer>;
  coreBusy?: () => boolean;
  productionChannelEnabled?: boolean;
};

function parseSemver(version: string): [number, number, number] | null {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version.trim());
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

export function compareSemver(a: string, b: string): number {
  const left = parseSemver(a);
  const right = parseSemver(b);
  if (!left || !right) throw new Error('invalid_semver');
  for (let i = 0; i < 3; i += 1) {
    if (left[i] > right[i]) return 1;
    if (left[i] < right[i]) return -1;
  }
  return 0;
}

export function canonicalManifestPayload(manifest: Omit<UpdateManifest, 'signature'>): string {
  return JSON.stringify({
    version: manifest.version,
    channel: manifest.channel,
    min_version: manifest.min_version,
    artifacts: manifest.artifacts.map((item) => ({
      url: item.url,
      sha256: item.sha256.toLowerCase(),
      size: item.size,
    })),
  });
}

export function signManifest(manifest: Omit<UpdateManifest, 'signature'>, secret: Buffer): string {
  return createHmac('sha256', secret).update(canonicalManifestPayload(manifest)).digest('hex');
}

export function verifyManifestSignature(manifest: UpdateManifest, secret: Buffer): boolean {
  const expected = Buffer.from(signManifest(manifest, secret), 'hex');
  const actual = Buffer.from(String(manifest.signature || ''), 'hex');
  if (expected.length === 0 || expected.length !== actual.length) return false;
  return timingSafeEqual(expected, actual);
}

export function assertHttpsAllowedUrl(urlString: string, allowedHosts: string[]): URL {
  let url: URL;
  try {
    url = new URL(urlString);
  } catch {
    throw new Error('invalid_url');
  }
  if (url.protocol !== 'https:') throw new Error('https_required');
  if (url.username || url.password) throw new Error('url_userinfo_forbidden');
  if (!allowedHosts.includes(url.hostname)) throw new Error('host_not_allowlisted');
  return url;
}

export function sha256Hex(buffer: Buffer): string {
  return createHash('sha256').update(buffer).digest('hex');
}

export class UpdateService {
  constructor(private readonly options: UpdateServiceOptions) {}

  async checkForUpdate(manifestUrl: string): Promise<UpdateDecision> {
    if (this.options.productionChannelEnabled !== true) {
      // Production auto-check stays disabled until channel policy is complete.
      // Local fixtures set productionChannelEnabled=true explicitly.
      return { status: 'rejected', reason: 'production_update_channel_blocked', checkId: 'update.channel' };
    }
    try {
      assertHttpsAllowedUrl(manifestUrl, this.options.allowedHosts);
      const manifest = await this.options.fetchManifest(manifestUrl);
      if (!verifyManifestSignature(manifest, this.options.trustSecret)) {
        return { status: 'rejected', reason: 'manifest_signature_invalid', checkId: 'update.reject-tamper' };
      }
      if (compareSemver(manifest.version, this.options.currentVersion) <= 0) {
        return { status: 'up_to_date' };
      }
      if (compareSemver(this.options.currentVersion, manifest.min_version) < 0) {
        // current is below min — still allow upgrade path, but block downgrade separately
      }
      const artifact = manifest.artifacts[0];
      if (!artifact) {
        return { status: 'rejected', reason: 'artifact_missing', checkId: 'update.reject-tamper' };
      }
      assertHttpsAllowedUrl(artifact.url, this.options.allowedHosts);
      return { status: 'available', version: manifest.version, artifact };
    } catch (error) {
      return {
        status: 'rejected',
        reason: error instanceof Error ? error.message : 'update_check_failed',
        checkId: 'update.reject-tamper',
      };
    }
  }

  async downloadAndVerify(artifact: UpdateArtifact): Promise<
    | { status: 'verified'; bytes: Buffer }
    | { status: 'rejected'; reason: string; checkId: string }
  > {
    if (this.options.coreBusy?.()) {
      return { status: 'rejected', reason: 'core_busy', checkId: 'update.deferred' };
    }
    try {
      assertHttpsAllowedUrl(artifact.url, this.options.allowedHosts);
      if (!this.options.downloadArtifact) {
        return { status: 'rejected', reason: 'downloader_missing', checkId: 'update.reject-tamper' };
      }
      const bytes = await this.options.downloadArtifact(artifact.url);
      if (bytes.byteLength !== artifact.size) {
        return { status: 'rejected', reason: 'size_mismatch', checkId: 'update.reject-tamper' };
      }
      if (sha256Hex(bytes) !== artifact.sha256.toLowerCase()) {
        return { status: 'rejected', reason: 'hash_mismatch', checkId: 'update.reject-tamper' };
      }
      return { status: 'verified', bytes };
    } catch (error) {
      return {
        status: 'rejected',
        reason: error instanceof Error ? error.message : 'download_failed',
        checkId: 'update.rollback',
      };
    }
  }

  evaluateInstallOutcome(installSucceeded: boolean): { status: 'applied' | 'rejected'; reason?: string; checkId: string } {
    if (installSucceeded) {
      return { status: 'applied', checkId: 'update.success' };
    }
    // Install failure must keep current version bootable.
    return { status: 'rejected', reason: 'install_failed_keep_current', checkId: 'update.rollback' };
  }
}
