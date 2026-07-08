import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GlassButton, GlassPanel, GlassPill, GlassToolbar } from './LiquidGlassPrimitives';

describe('LiquidGlassPrimitives', () => {
  it('renders reusable liquid glass buttons with stable variants', () => {
    render(<GlassButton variant="primary">开始任务</GlassButton>);

    const button = screen.getByRole('button', { name: '开始任务' });
    expect(button).toHaveClass('biotGlassButton');
    expect(button).toHaveClass('is-primary');
    expect(button).not.toHaveClass('is-ghost');
  });

  it('keeps button type, icon and disabled state explicit', () => {
    render(
      <GlassButton icon={<span data-testid="button-icon" />} disabled>
        执行一步
      </GlassButton>,
    );

    const button = screen.getByRole('button', { name: '执行一步' });
    expect(button).toHaveAttribute('type', 'button');
    expect(button).toBeDisabled();
    expect(screen.getByTestId('button-icon')).toBeInTheDocument();
  });

  it('renders panels, pills and toolbars without private address wording', () => {
    render(
      <GlassPanel title="权限状态" description="写入前等待人工批准" tone="strong" flow>
        <GlassToolbar ariaLabel="快捷操作">
          <GlassPill tone="warning">完全访问</GlassPill>
          <GlassButton variant="ghost">刷新权限</GlassButton>
        </GlassToolbar>
      </GlassPanel>,
    );

    expect(screen.getByRole('region', { name: '权限状态' })).toHaveClass('biotGlassPanel');
    expect(screen.getByText('写入前等待人工批准')).toBeInTheDocument();
    expect(screen.getByText('完全访问')).toHaveClass('biotGlassPill', 'is-warning');
    expect(screen.getByLabelText('快捷操作')).toHaveClass('biotGlassToolbar');
    expect(document.body.textContent).not.toContain(String.fromCharCode(0x7238));
  });
});
