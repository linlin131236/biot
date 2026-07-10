/**
 * M36 Main process security test: verifies BrowserWindow webPreferences
 * and workspace picker IPC registration.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const mainSource = readFileSync(join(__dirname, 'main.ts'), 'utf-8');
const workspacePickerSource = readFileSync(join(__dirname, 'workspacePicker.ts'), 'utf-8');

describe('main process security', () => {
  it('registers Agent Core IPC against the supervisor verified generation', () => {
    expect(mainSource).toContain('registerAgentCoreIpc');
    expect(mainSource).toContain('getVerifiedGeneration');
    expect(mainSource).not.toContain('process.env.BOLT_AGENT_CORE_TOKEN =');
    expect(mainSource).not.toContain('process.env.BOLT_AGENT_CORE_PORT =');
  });

  it('sets contextIsolation to true', () => {
    expect(mainSource).toContain('contextIsolation: true');
  });

  it('disables nodeIntegration', () => {
    expect(mainSource).toContain('nodeIntegration: false');
  });

  it('references preload.cjs', () => {
    expect(mainSource).toContain('preload.cjs');
  });

  it('does not enable remote module', () => {
    expect(mainSource).not.toContain('enableRemoteModule');
  });

  it('registers workspace picker IPC via registerWorkspacePickerIpc', () => {
    expect(mainSource).toContain('registerWorkspacePickerIpc');
  });

  it('denies new windows and blocks unexpected navigation', () => {
    expect(mainSource).toContain('setWindowOpenHandler');
    expect(mainSource).toContain("action: 'deny'");
    expect(mainSource).toContain('will-navigate');
    expect(mainSource).toContain('event.preventDefault()');
  });

  it('uses bolt:select-workspace channel in workspacePicker', () => {
    expect(workspacePickerSource).toContain('bolt:select-workspace');
  });

  it('workspacePicker only allows openDirectory', () => {
    expect(workspacePickerSource).toContain('openDirectory');
  });
});
