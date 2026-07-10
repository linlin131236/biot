export type TrustedSenderEvent = {
  sender: { id: number };
  senderFrame?: {
    url?: string;
    parent?: unknown;
    top?: unknown;
  } | null;
};

export type SenderTrustOptions = {
  trustedWebContentsId: number | null;
  packaged: boolean;
  appPath: string;
  devServerUrl?: string | null;
  allowedEntryPathnames?: string[];
};

function toForwardSlashes(value: string): string {
  const bs = String.fromCharCode(92);
  return value.split(bs).join('/');
}

function stripLeadingSlashes(value: string): string {
  let out = value;
  while (out.startsWith('/')) out = out.slice(1);
  return out;
}

export function normalizeComparableUrl(urlString: string): string | null {
  try {
    const url = new URL(urlString);
    if (url.username || url.password) return null;
    if (url.hash) return null;
    if (url.protocol === 'file:') {
      // Exact entry only: no query/search/hash/userinfo.
      if (url.search) return null;
      let pathname = decodeURIComponent(url.pathname);
      if (process.platform === 'win32' && pathname.startsWith('/')) pathname = pathname.slice(1);
      pathname = stripLeadingSlashes(toForwardSlashes(pathname)).toLowerCase();
      return `file:///${pathname}`;
    }
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      // Exact origin + pathname + search. No startsWith/prefix matching.
      const pathname = url.pathname || '/';
      return `${url.protocol}//${url.host}${pathname}${url.search}`;
    }
    return null;
  } catch {
    return null;
  }
}

export function expectedPackagedEntryUrl(appPath: string): string {
  const cleaned = stripLeadingSlashes(toForwardSlashes(appPath)).toLowerCase();
  return `file:///${cleaned}/dist/index.html`;
}

export function isExactDevEntryUrl(urlString: string, devServerUrl: string, allowedEntryPathnames: string[] = ['/', '/index.html']): boolean {
  let expectedOrigin: string;
  try {
    const base = new URL(devServerUrl);
    if (base.username || base.password) return false;
    expectedOrigin = base.origin;
  } catch {
    return false;
  }
  let actual: URL;
  try {
    actual = new URL(urlString);
  } catch {
    return false;
  }
  if (actual.username || actual.password) return false;
  if (actual.hash) return false;
  if (actual.origin !== expectedOrigin) return false;
  const pathname = actual.pathname || '/';
  return allowedEntryPathnames.includes(pathname);
}

export function isAllowedNavigationUrl(urlString: string, options: Pick<SenderTrustOptions, 'packaged' | 'appPath' | 'devServerUrl' | 'allowedEntryPathnames'>): boolean {
  if (options.devServerUrl) {
    return isExactDevEntryUrl(urlString, options.devServerUrl, options.allowedEntryPathnames);
  }
  if (!options.packaged) return false;
  const actual = normalizeComparableUrl(urlString);
  if (!actual) return false;
  return actual === expectedPackagedEntryUrl(options.appPath);
}

export function isTrustedDesktopSender(event: TrustedSenderEvent, options: SenderTrustOptions): boolean {
  if (options.trustedWebContentsId == null) return false;
  if (event.sender.id !== options.trustedWebContentsId) return false;
  const frame = event.senderFrame;
  if (!frame || typeof frame.url !== 'string' || !frame.url) return false;
  // Require top-level frame only.
  if (frame.parent != null && frame.parent !== frame) return false;
  if (frame.top != null && frame.top !== frame) return false;
  return isAllowedNavigationUrl(frame.url, options);
}
