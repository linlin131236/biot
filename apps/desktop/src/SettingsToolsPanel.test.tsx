import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SettingsToolsPanel } from './SettingsToolsPanel';

const data = { budget: {}, model_config: { provider: 'TestAI', status: '已就绪' }, tool_policy: { mode: 'PermissionGate', description: '需审批' } };

describe('SettingsToolsPanel', () => {
  it('empty', async () => { render(<SettingsToolsPanel baseUrl="t" api={{ fetchSettingsTools: vi.fn().mockResolvedValue(data) }} />); await waitFor(() => expect(screen.getByText(/TestAI/)).toBeTruthy()); });
  it('readonly', async () => { render(<SettingsToolsPanel baseUrl="t" api={{ fetchSettingsTools: vi.fn().mockResolvedValue(data) }} />); await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy()); });
  it('nosecret', async () => { render(<SettingsToolsPanel baseUrl="t" api={{ fetchSettingsTools: vi.fn().mockResolvedValue(data) }} />); await waitFor(() => expect(screen.queryByText(/secret|token|key|api_key/i)).toBeNull()); });
});
