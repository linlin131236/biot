import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('Liquid Glass design tokens', () => {
  it('defines shared dark and light Liquid Glass tokens', () => {
    const css = readFileSync(join(__dirname, 'liquidGlassShell.css'), 'utf-8');

    expect(css).toContain('--surface-base');
    expect(css).toContain('--surface-depth');
    expect(css).toContain('--glass-panel');
    expect(css).toContain('--glass-panel-strong');
    expect(css).toContain('--accent-primary');
    expect(css).toContain('--accent-warning');
    expect(css).toContain('[data-theme="light"]');
    expect(css).toContain('.biotLiquidBorder::before');
    expect(css).toContain('animation: biotBorderFlow');
  });
});
