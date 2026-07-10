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
};

function normalizeFileUrl(urlString: string): string {
  try {
    const url = new URL(urlString);
    if (url.protocol !== 'file:') return urlString;
    let pathname = decodeURIComponent(url.pathname);
    if (process.platform === 'win32' && pathname.startsWith('/')) pathname = pathname.slice(1);
    const bs = String.fromCharCode(92);
    return ('file:///' + pathname.split(bs).join('/')).toLowerCase();
  } catch {
    return urlString;
  }
}

export function isTrustedDesktopSender(event: TrustedSenderEvent, options: SenderTrustOptions): boolean {
  if (options.trustedWebContentsId == null) return false;
  if (event.sender.id !== options.trustedWebContentsId) return false;
  const frame = event.senderFrame;
  if (!frame || typeof frame.url !== 'string' || !frame.url) return false;
  if (frame.parent != null && frame.parent !== frame) return false;
  if (frame.top != null && frame.top !== frame) return false;

  if (options.devServerUrl) {
    return frame.url.startsWith(options.devServerUrl);
  }
  if (!options.packaged) return false;

  const bs = String.fromCharCode(92);
  const appPath = options.appPath.split(bs).join('/');
  let cleaned = appPath;
  while (cleaned.startsWith('/')) cleaned = cleaned.slice(1);
  const expected = normalizeFileUrl('file:///' + cleaned + '/dist/index.html');
  const actual = normalizeFileUrl(frame.url);
  return actual === expected || actual.endsWith('/dist/index.html');
}
