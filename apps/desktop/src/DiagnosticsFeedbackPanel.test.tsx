import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DiagnosticsFeedbackPanel } from './DiagnosticsFeedbackPanel';

describe('DiagnosticsFeedbackPanel', () => {
  it('loads redacted summary and exposes copy/open/disable actions', async () => {
    const api = {
      exportSummary: vi.fn().mockResolvedValue('{"upload":"disabled_by_default","events":[]}'),
      openDiagnosticsDir: vi.fn().mockResolvedValue(undefined),
      setCollectionEnabled: vi.fn().mockResolvedValue(undefined),
      getCollectionEnabled: vi.fn().mockResolvedValue(true),
    };
    render(<DiagnosticsFeedbackPanel api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '刷新脱敏诊断' }));
    await waitFor(() => expect(api.exportSummary).toHaveBeenCalled());
    expect(await screen.findByText(/disabled_by_default/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '打开日志目录' }));
    await waitFor(() => expect(api.openDiagnosticsDir).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: '关闭崩溃收集' }));
    await waitFor(() => expect(api.setCollectionEnabled).toHaveBeenCalledWith(false));
  });
});
