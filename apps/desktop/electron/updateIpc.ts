import { UpdateService, type UpdateDecision } from './updateService.js';

type IpcMainLike = {
  handle: (channel: string, listener: (event: unknown, ...args: unknown[]) => unknown) => void;
};

export type UpdateIpcDependencies = {
  isTrustedSender: (event: { sender: { id: number } }) => boolean;
  currentVersion: string;
  allowedHosts?: string[];
  trustSecret?: Buffer;
  productionChannelEnabled?: boolean;
  coreBusy?: () => boolean;
  service?: UpdateService;
};

const CHANNELS = {
  status: 'bolt:update:status',
  check: 'bolt:update:check',
} as const;

export function createDefaultUpdateService(dependencies: UpdateIpcDependencies): UpdateService {
  return new UpdateService({
    currentVersion: dependencies.currentVersion,
    allowedHosts: dependencies.allowedHosts ?? ['updates.bolt.local'],
    trustSecret: dependencies.trustSecret ?? Buffer.from('bolt-dev-not-for-production'),
    productionChannelEnabled: dependencies.productionChannelEnabled === true,
    coreBusy: dependencies.coreBusy,
    fetchManifest: async () => {
      throw new Error('production_update_channel_blocked');
    },
  });
}

export function registerUpdateIpc(ipcMain: IpcMainLike, dependencies: UpdateIpcDependencies): UpdateService {
  const service = dependencies.service ?? createDefaultUpdateService(dependencies);

  ipcMain.handle(CHANNELS.status, (event) => {
    assertTrusted(event, dependencies);
    return {
      productionChannelEnabled: dependencies.productionChannelEnabled === true,
      currentVersion: dependencies.currentVersion,
      policy: 'manual_check_only_until_channel_ready',
    };
  });

  ipcMain.handle(CHANNELS.check, async (event, payload) => {
    assertTrusted(event, dependencies);
    const body = (payload ?? {}) as { manifestUrl?: string };
    if (!body.manifestUrl) {
      return {
        status: 'rejected',
        reason: 'production_update_channel_blocked',
        checkId: 'update.channel',
      } satisfies UpdateDecision;
    }
    return service.checkForUpdate(body.manifestUrl);
  });

  return service;
}

function assertTrusted(event: unknown, dependencies: UpdateIpcDependencies): void {
  const typed = event as { sender: { id: number } };
  if (!dependencies.isTrustedSender(typed)) {
    throw new Error('untrusted update sender');
  }
}

export const updateChannels = CHANNELS;
