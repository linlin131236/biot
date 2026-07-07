import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DiagnosticsCenterPanel } from './DiagnosticsCenterPanel';

function fakeApi(data: Record<string, unknown>) {
  return { fetchDiagnosticsCenter: vi.fn().mockResolvedValue(data) };
}

const emptyData = { diagnostics: [], integrity: [], total_blockers: 0, total_warnings: 0, total_infos: 0 };
const blockerData = {
  diagnostics: [{ code: 'D001', severity: 'blocking', severity_label: '阻断', summary: '测试阻断', suggestion: '修复建议' }],
  integrity: [],
  total_blockers: 1, total_warnings: 0, total_infos: 0,
};

describe('DiagnosticsCenterPanel', () => {
  it('renders loading', () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(emptyData)} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('renders empty', async () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(emptyData)} />);
    await waitFor(() => expect(screen.getByText(/暂无诊断项/)).toBeTruthy());
  });

  it('shows blocker', async () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(blockerData)} />);
    await waitFor(() => expect(screen.getByText('测试阻断')).toBeTruthy());
  });

  it('shows suggestion', async () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(blockerData)} />);
    await waitFor(() => expect(screen.getByText(/修复建议/)).toBeTruthy());
  });

  it('shows summary counts', async () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(blockerData)} />);
    await waitFor(() => expect(screen.getByText('1')).toBeTruthy());
  });

  it('has read-only note', async () => {
    render(<DiagnosticsCenterPanel baseUrl="http://t" api={fakeApi(emptyData)} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
  });
});
