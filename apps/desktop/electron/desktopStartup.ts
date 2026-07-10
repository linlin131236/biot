type CoreStartupStatus = {
  status: 'ok' | 'down';
  error?: string;
};

export async function startDesktopWindow(dependencies: {
  startCore: () => Promise<CoreStartupStatus>;
  createWindow: () => Promise<void>;
}): Promise<void> {
  const status = await dependencies.startCore();
  if (status.status !== 'ok') {
    throw new Error(status.error ?? 'Agent Core startup failed');
  }
  await dependencies.createWindow();
}
