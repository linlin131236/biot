import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DesktopBetaShipPanel } from './DesktopBetaShipPanel';
import { fetchDesktopBetaShip } from './harnessClientAutonomy';

function resultFixture(overrides: Record<string, unknown> = {}) {
  return {
    ready: true,
    all_passed: true,
    total: 10,
    passed_count: 10,
    failed_count: 0,
    p1_failures: [],
    warnings: [],
    next_step: 'M180 通过后只允许人工复审；不自动 release/tag/delete/push。',
    checks: [
      { name: 'M171 桌面打包 smoke 就绪', passed: true, detail: '脚本存在', severity: 'info' },
      { name: 'M180 Beta Release Candidate Gate 就绪', passed: true, detail: '文档完整', severity: 'info' },
    ],
    ...overrides,
  };
}

describe('fetchDesktopBetaShip', () => {
  it('uses the authenticated fetcher and reads the beta ship endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(resultFixture()), { status: 200 }));

    const result = await fetchDesktopBetaShip(fetcher);

    expect(fetcher).toHaveBeenCalledWith('/desktop/beta-ship');
    expect(result.ready).toBe(true);
  });
});

describe('DesktopBetaShipPanel', () => {
  it('shows Chinese release candidate status with injected fetcher', async () => {
    const api = { fetchBetaShip: vi.fn().mockResolvedValue(resultFixture()) };
    const fetcher = vi.fn();

    render(<DesktopBetaShipPanel fetcher={fetcher} api={api} />);

    await waitFor(() => expect(api.fetchBetaShip).toHaveBeenCalledWith(fetcher));
    expect(await screen.findByText('桌面 Beta 发布候选')).toBeTruthy();
    expect(screen.getByText('可以进入人工复审')).toBeTruthy();
    expect(screen.getByText('M171 桌面打包 smoke 就绪')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /release|push|tag|delete/i })).toBeNull();
  });

  it('shows blockers when beta ship gate is not ready', async () => {
    const api = {
      fetchBetaShip: vi.fn().mockResolvedValue(resultFixture({
        ready: false,
        all_passed: false,
        failed_count: 1,
        p1_failures: ['M178 安装包发布前检查就绪'],
        checks: [{ name: 'M178 安装包发布前检查就绪', passed: false, detail: '安装包脚本缺失', severity: 'blocking' }],
      })),
    };

    render(<DesktopBetaShipPanel fetcher={vi.fn()} api={api} />);

    expect(await screen.findByText('存在阻断项')).toBeTruthy();
    expect(screen.getAllByText('M178 安装包发布前检查就绪').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('安装包脚本缺失')).toBeTruthy();
  });
});
