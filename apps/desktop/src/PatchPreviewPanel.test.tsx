/**
 * PatchPreviewPanel tests (M107 + M155).
 */
import { describe, it, expect } from 'vitest';
import { act, fireEvent } from '@testing-library/react';
import { render, screen, waitFor } from '@testing-library/react';
import { PatchPreviewPanel } from './PatchPreviewPanel';

const makePatchList = () => [
  {
    patch_id: 'patch_abc123',
    description: '添加日志到 main.py',
    risk_level: 'low',
    risk_label: '低',
    status: 'pending',
    status_label: '待批准',
    total_files: 1,
    total_lines: 4,
    audit_hash: 'abc123def456',
  },
];

const makePatchPreview = () => ({
  patch_id: 'patch_abc123',
  description: '添加日志到 main.py',
  risk_level: 'low',
  risk_label: '低',
  total_files: 1,
  total_lines: 4,
  files: [{ path: 'src/main.py', operation: '修改', hunk_count: 1 }],
  unified_diff: '--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1,2 @@\n print("hello")\n+print("world")',
  disclaimer: '此补丁仅用于预览',
});

describe('PatchPreviewPanel', () => {
  it('renders loading state', () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => new Promise(() => {})}
        fetchPatchPreview={() => new Promise(() => {})}
      />
    );
    expect(screen.getByText(/加载补丁列表中/)).toBeDefined();
  });

  it('renders empty state', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: [] })}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    expect(await screen.findByText(/暂无补丁提案/)).toBeDefined();
  });

  it('renders error state', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.reject(new Error('网络错误'))}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    expect(await screen.findByText(/加载失败/)).toBeDefined();
  });

  it('renders patch list', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    expect(await screen.findByText(/添加日志到 main.py/)).toBeDefined();
  });

  it('shows risk badge', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    expect(await screen.findByText('低')).toBeDefined();
  });

  it('shows Chinese disclaimer', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    expect(await screen.findByText(/此面板仅用于预览/)).toBeDefined();
  });

  it('shows Chinese risk explanation', async () => {
    const preview = {
      ...makePatchPreview(),
      risk_level: 'high',
      risk_label: '高',
    };
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(preview)}
      />
    );
    await waitFor(() => expect(screen.getByText(/添加日志到 main.py/)).toBeDefined());
    act(() => {
      fireEvent.click(screen.getByText(/添加日志到 main.py/));
    });
    await waitFor(() => expect(screen.getByText(/建议逐行审查/)).toBeDefined());
  });

  it('renders multi-file patch list', async () => {
    const multiFilePreview = {
      ...makePatchPreview(),
      total_files: 3,
      total_lines: 25,
      files: [
        { path: 'src/main.py', operation: '修改', hunk_count: 2 },
        { path: 'src/utils.py', operation: '新增', hunk_count: 1 },
        { path: 'old/config.json', operation: '删除', hunk_count: 1 },
      ],
    };
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(multiFilePreview)}
      />
    );
    await waitFor(() => expect(screen.getByText(/添加日志到 main.py/)).toBeDefined());
    act(() => {
      fireEvent.click(screen.getByText(/添加日志到 main.py/));
    });
    await waitFor(() => {
      expect(screen.getByText('src/main.py')).toBeDefined();
      expect(screen.getByText('src/utils.py')).toBeDefined();
      expect(screen.getByText('old/config.json')).toBeDefined();
    });
  });

  it('does not render diff preview when unified_diff is empty', async () => {
    const emptyDiffPreview = {
      ...makePatchPreview(),
      unified_diff: '',
    };
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(emptyDiffPreview)}
      />
    );
    await waitFor(() => expect(screen.getByText(/添加日志到 main.py/)).toBeDefined());
    expect(screen.queryByText(/Diff 预览/)).toBeNull();
  });

  it('has no execute buttons', async () => {
    render(
      <PatchPreviewPanel
        fetchPatchList={() => Promise.resolve({ patches: makePatchList() })}
        fetchPatchPreview={() => Promise.resolve(makePatchPreview())}
      />
    );
    await waitFor(() => expect(screen.getByText(/添加日志到 main.py/)).toBeDefined());
    const buttons = document.querySelectorAll('button');
    expect(buttons.length).toBe(0);
  });
});
