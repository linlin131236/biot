import { createHash } from 'node:crypto';
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

const TEXT_EXTENSIONS = new Set(['.js', '.mjs', '.cjs', '.json', '.txt', '.md', '.html', '.css', '.map', '.yml', '.yaml', '.toml', '.py', '.env', '.xml']);
const FORBIDDEN_NAME_SUFFIXES = ['.env', '.pfx', '.p12', '.key'];
const SECRET_CONTENT_PATTERNS = [
  { id: 'dotenv_assignment', re: /(?:^|\n)\s*(?:API_KEY|OPENAI_API_KEY|BOLT_CORE_BEARER|CSC_KEY_PASSWORD)\s*=\s*['"]?[^'"\n]{8,}/i },
  { id: 'openai_live_key', re: /\bsk-[A-Za-z0-9]{20,}\b/ },
  { id: 'bearer_live', re: /\bBearer\s+[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{10,}\b/ },
  { id: 'private_key_block', re: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
  { id: 'core_url_config', re: /\bcoreUrl\s*=\s*['"]https?:\/\//i },
  { id: 'dev_server', re: /\bVITE_DEV_SERVER_URL\b\s*[:=]\s*['"]https?:\/\// },
  { id: 'default_core_url', re: /\bDEFAULT_CORE_URL\b\s*=\s*['"]https?:\/\// },
  { id: 'agent_core_endpoint_assign', re: /\bagentCoreEndpoint\b\s*[:=]\s*['"]https?:\/\// },
];

export function listFilesRecursive(root) {
  const out = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === '__pycache__' || entry.name === 'node_modules') continue;
        walk(full);
      } else if (entry.isFile()) {
        out.push(full);
      }
    }
  };
  walk(root);
  return out;
}

export function resolveAsarModule() {
  const candidates = [
    '@electron/asar',
    join(process.cwd(), 'node_modules/.pnpm/@electron+asar@3.4.1/node_modules/@electron/asar'),
  ];
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      // continue
    }
  }
  return null;
}

export function listAsarEntries(asarPath) {
  const asar = resolveAsarModule();
  if (!asar) return null;
  try {
    return asar.listPackage(asarPath).map((entry) => String(entry).split(String.fromCharCode(92)).join('/'));
  } catch (error) {
    return null;
  }
}

export function readAsarFile(asarPath, entryPath) {
  const asar = resolveAsarModule();
  if (!asar) return null;
  try {
    return asar.extractFile(asarPath, entryPath);
  } catch {
    return null;
  }
}

export function sha256File(path) {
  const hash = createHash('sha256');
  hash.update(readFileSync(path));
  return hash.digest('hex');
}

function patternsForPath(rel) {
  const lower = rel.toLowerCase();
  if (lower.includes('agent-core/src/') || lower.includes('resources/agent-core/src/')) {
    return SECRET_CONTENT_PATTERNS.filter((pattern) =>
      ['openai_live_key', 'bearer_live', 'private_key_block'].includes(pattern.id),
    );
  }
  return SECRET_CONTENT_PATTERNS;
}

function shouldScanContent(rel) {
  const lower = rel.toLowerCase();
  if (lower.includes('/.venv/') || lower.includes('/site-packages/')) return false;
  if (lower.endsWith('.pem') && lower.includes('cacert')) return false;
  // Agent Core source intentionally contains redaction fixtures and API field names.
  // Release secret scan focuses on package shell assets and config leaks, not library source text.
  if (lower.includes('evidence_redactor') || lower.includes('dogfood') || lower.includes('.test.')) return false;
  return true;
}

export function scanReleaseArtifacts(packageRoot) {
  const findings = [];
  if (!packageRoot || !existsSync(packageRoot)) {
    return { ok: false, findings: [`missing package root: ${packageRoot ?? '<empty>'}`], files: [] };
  }
  const files = listFilesRecursive(packageRoot);
  const records = [];
  for (const full of files) {
    const rel = relative(packageRoot, full).split(sep).join('/');
    const lower = rel.toLowerCase();
    for (const suffix of FORBIDDEN_NAME_SUFFIXES) {
      if (lower.endsWith(suffix)) findings.push(`forbidden file ${rel}`);
    }
    if (lower === '.env' || lower.endsWith('/.env') || /(^|\/)\.env\./.test(lower)) {
      findings.push(`forbidden file ${rel}`);
    }
    const size = statSync(full).size;
    records.push({ path: rel, size, sha256: sha256File(full) });
    if (!shouldScanContent(rel)) continue;
    const ext = lower.includes('.') ? `.${lower.split('.').pop()}` : '';
    if (size > 0 && size < 1_500_000 && (TEXT_EXTENSIONS.has(ext) || lower.endsWith('license'))) {
      let text;
      try {
        text = readFileSync(full, 'utf8');
      } catch {
        continue;
      }
      for (const pattern of patternsForPath(rel)) {
        if (pattern.re.test(text)) findings.push(`forbidden content ${pattern.id} in ${rel}`);
      }
      if (!rel.endsWith('.asar') && /[A-Za-z]:\\Users\\[^\\\s"']+/i.test(text)) {
        findings.push(`absolute user path in ${rel}`);
      }
    }
  }
  const asarFile = files.find((full) => relative(packageRoot, full).split(sep).join('/').endsWith('app.asar'));
  let asarEntries = null;
  if (asarFile) {
    asarEntries = listAsarEntries(asarFile);
    if (asarEntries) {
      for (const entry of asarEntries) {
        // scan asar content for packaged renderer/main secrets
        const lower = entry.toLowerCase();
        for (const suffix of FORBIDDEN_NAME_SUFFIXES) {
          if (lower.endsWith(suffix)) findings.push(`forbidden asar entry ${entry}`);
        }
        if (lower.endsWith('.env') || /(^|\/)\.env(\.|$)/.test(lower)) findings.push(`forbidden asar entry ${entry}`);
      
        const lowerEntry = String(entry).toLowerCase();
        const ext = lowerEntry.includes('.') ? `.${lowerEntry.split('.').pop()}` : '';
        if (['.js', '.mjs', '.cjs', '.json', '.css', '.html', '.map', '.txt', '.md'].includes(ext)) {
          const bytes = readAsarFile(asarFile, entry);
          if (bytes) {
            const textContent = Buffer.from(bytes).toString('utf8');
            if (textContent.length > 0 && textContent.length < 1500000) {
              for (const pattern of patternsForPath(rel)) {
                if (pattern.re.test(textContent)) findings.push(`forbidden content ${pattern.id} in resources/app.asar:${entry}`);
              }
            }
          }
        }
      }
      records.push({
        path: 'resources/app.asar#listing',
        size: asarEntries.length,
        sha256: createHash("sha256").update(asarEntries.join(String.fromCharCode(10))).digest("hex"),
      });
    } else {
      findings.push('asar_listing_unavailable');
    }
  }
  const uniqueFindings = [...new Set(findings)];
  return {
    ok: uniqueFindings.length === 0,
    findings: uniqueFindings,
    files: records.sort((a, b) => a.path.localeCompare(b.path)),
    asar_listing: asarEntries ? 'present' : (asarFile ? 'unavailable' : 'absent'),
  };
}

export function writeReleaseEvidence({ outputDir, version, commit, packageRoot, scan, environment }) {
  mkdirSync(outputDir, { recursive: true });
  const artifacts = {
    version,
    commit,
    package_root_role: 'install_dir_or_win_unpacked',
    files: scan.files,
  };
  const checks = {
    'artifact.sha256': scan.files.length > 0 ? 'passed' : 'failed',
    'artifact.secret-scan': scan.ok ? 'passed' : 'failed',
    'artifact.sbom': 'passed_with_limitations',
    'artifact.asar-listing': scan.asar_listing === 'present' || scan.asar_listing === 'absent' ? 'passed' : 'blocked',
  };
  const sbom = {
    version,
    commit,
    generator: 'scripts/scan-release-artifacts.mjs',
    package_manager_hint: 'pnpm+uv',
    sbom_kind: 'file_inventory_not_cyclonedx',
    limitations: ['Not CycloneDX/SPDX dependency SBOM', 'asar listing depends on @electron/asar'],
    asar_listing: scan.asar_listing ?? 'unknown',
    file_count: scan.files.length,
    total_bytes: scan.files.reduce((sum, file) => sum + file.size, 0),
  };
  const manifest = {
    version,
    commit,
    created_at_utc: new Date().toISOString(),
    package_root_role: 'install_dir_or_win_unpacked',
  };
  writeFileSync(join(outputDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(join(outputDir, 'environment.json'), `${JSON.stringify(environment, null, 2)}\n`);
  writeFileSync(join(outputDir, 'artifacts.json'), `${JSON.stringify(artifacts, null, 2)}\n`);
  writeFileSync(join(outputDir, 'checks.json'), `${JSON.stringify(checks, null, 2)}\n`);
  writeFileSync(join(outputDir, 'sbom.json'), `${JSON.stringify(sbom, null, 2)}\n`);
  writeFileSync(
    join(outputDir, 'events.ndjson'),
    `${JSON.stringify({ id: 'scan-complete', status: scan.ok ? 'passed' : 'failed', findings: scan.findings.length })}\n`,
  );
  return { manifest, checks, sbom, findings: scan.findings };
}

export function main(repoRoot = dirname(dirname(fileURLToPath(import.meta.url)))) {
  const pathIdx = process.argv.indexOf('--path');
  const outIdx = process.argv.indexOf('--out');
  const packageRoot = pathIdx >= 0 ? process.argv[pathIdx + 1] : join(repoRoot, 'apps/desktop/release/win-unpacked');
  const version = JSON.parse(readFileSync(join(repoRoot, 'apps/desktop/package.json'), 'utf8')).version;
  const commit = process.env.BOLT_RELEASE_COMMIT || 'unknown';
  const scan = scanReleaseArtifacts(packageRoot);
  if (!scan.ok) {
    console.error(`Release artifact scan failed:\n${scan.findings.join('\n')}`);
  } else {
    console.log(`Release artifact scan passed (${scan.files.length} files, asar=${scan.asar_listing}).`);
  }
  if (outIdx >= 0) {
    const outputDir = process.argv[outIdx + 1];
    writeReleaseEvidence({
      outputDir,
      version,
      commit,
      packageRoot,
      scan,
      environment: {
        node: process.version,
        platform: process.platform,
        arch: process.arch,
      },
    });
    console.log(`Evidence written to ${outputDir}`);
  }
  if (!scan.ok) process.exitCode = 1;
  return scan;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
