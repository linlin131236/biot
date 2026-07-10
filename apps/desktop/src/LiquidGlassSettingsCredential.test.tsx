import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiquidGlassSettings } from './LiquidGlassSettings';


describe('LiquidGlassSettings credential surface', () => {
  it('renders the real credential form inside model settings', () => {
    render(<LiquidGlassSettings
      activeSetting="model"
      onBack={vi.fn()}
      setActiveSetting={vi.fn()}
      settings={{
        theme: 'dark',
        language: 'zh-CN',
        default_workspace: 'D:/Bolt/Bolt',
        has_api_key: false,
        credential_revision: 0,
      }}
      onSaveTheme={vi.fn()}
    />);

    expect(screen.getByRole('region', { name: '模型提供方概览' })).toBeInTheDocument();
    expect(screen.getByText('API 密钥')).toBeInTheDocument();
    expect(screen.getByText('仅状态可见')).toBeInTheDocument();
    expect(screen.getByText('未配置')).toBeInTheDocument();
    // Credential input is not mirrored into settings; only configuration status is shown.
    expect(screen.queryByLabelText('API 密钥')).not.toBeInTheDocument();
  });
});
