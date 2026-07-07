import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { FailureExplanationPanel } from './FailureExplanationPanel';

const empty = { failures: [], total: 0 };
const full = { failures: [{ id: 'f1', category: 'api', category_cn: 'API错误', summary: '连接超时', suggestion: '检查网络', retryable: true, occurred_at: '2026-01-01' }], total: 1 };

describe('FailureExplanationPanel', () => {
  it('empty', async () => { render(<FailureExplanationPanel baseUrl="t" api={{ fetchFailureExplanation: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/暂无失败/)).toBeTruthy()); });
  it('full', async () => { render(<FailureExplanationPanel baseUrl="t" api={{ fetchFailureExplanation: vi.fn().mockResolvedValue(full) }} />); await waitFor(() => expect(screen.getByText('连接超时')).toBeTruthy()); });
  it('readonly', async () => { render(<FailureExplanationPanel baseUrl="t" api={{ fetchFailureExplanation: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy()); });
});
