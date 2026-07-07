/**
 * PatchPreviewPanel — 中文补丁预览面板 (M107)。
 * 展示补丁提案：涉及文件、变更统计、风险等级、diff 预览。
 * 纯只读，无执行/批准按钮。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface PatchFileInfo {
  path: string;
  operation: string;
  hunk_count: number;
}

interface PatchPreview {
  patch_id: string;
  description: string;
  risk_level: string;
  risk_label: string;
  total_files: number;
  total_lines: number;
  files: PatchFileInfo[];
  unified_diff: string;
  disclaimer: string;
}

interface PatchListItem {
  patch_id: string;
  description: string;
  risk_level: string;
  risk_label: string;
  status: string;
  status_label: string;
  total_files: number;
  total_lines: number;
  audit_hash: string;
}

interface Props {
  fetchPatchList: () => Promise<{ patches: PatchListItem[] }>;
  fetchPatchPreview: (patchId: string) => Promise<PatchPreview>;
}

type LoadState = 'loading' | 'loaded' | 'error' | 'empty';

export function PatchPreviewPanel({ fetchPatchList, fetchPatchPreview }: Props) {
  const [state, setState] = useState<LoadState>('loading');
  const [error, setError] = useState('');
  const [patches, setPatches] = useState<PatchListItem[]>([]);
  const [selectedPatch, setSelectedPatch] = useState<PatchPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    fetchPatchList()
      .then((data) => {
        if (cancelled) return;
        if (data.patches.length === 0) {
          setState('empty');
        } else {
          setPatches(data.patches);
          setState('loaded');
        }
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message ?? '加载补丁列表失败');
        setState('error');
      });
    return () => { cancelled = true; };
  }, [fetchPatchList]);

  function handlePreview(patchId: string) {
    setPreviewLoading(true);
    fetchPatchPreview(patchId)
      .then((data) => {
        setSelectedPatch(data);
        setPreviewLoading(false);
      })
      .catch((e) => {
        setError(e?.message ?? '加载补丁预览失败');
        setPreviewLoading(false);
      });
  }

  function riskColor(level: string): string {
    if (level === 'critical' || level === 'high') return '#dc2626';
    if (level === 'medium') return '#d97706';
    return '#6b7280';
  }

  // ── Loading ──
  if (state === 'loading') {
    return (
      <div style={{ padding: '12px 16px' }}>
        <p style={{ color: '#6b7280', fontSize: 14 }}>加载补丁列表中...</p>
      </div>
    );
  }

  // ── Error ──
  if (state === 'error') {
    return (
      <div style={{ padding: '12px 16px' }}>
        <p style={{ color: '#dc2626', fontSize: 14 }}>加载失败：{error}</p>
        <p style={{ color: '#6b7280', fontSize: 12, marginTop: 4 }}>
          请确认后端服务正常运行后刷新页面。
        </p>
      </div>
    );
  }

  // ── Empty ──
  if (state === 'empty') {
    return (
      <div style={{ padding: '12px 16px' }}>
        <p style={{ color: '#6b7280', fontSize: 14 }}>暂无补丁提案</p>
        <p style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
          当写入工具生成补丁提案后，将在此显示中文预览和风险评估。
        </p>
      </div>
    );
  }

  // ── Normal ──
  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      {/* Disclaimer */}
      <div style={{
        background: '#fef3c7', border: '1px solid #fcd34d',
        borderRadius: 4, padding: '6px 10px', marginBottom: 12,
        fontSize: 12, color: '#92400e',
      }}>
        此面板仅用于预览补丁提案，不执行任何写入操作。所有补丁需爸爸批准后方可应用。
      </div>

      {/* Patch list */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>
          补丁提案列表（{patches.length}）
        </h3>
        <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 4 }}>
          {patches.map((p) => (
            <div
              key={p.patch_id}
              onClick={() => handlePreview(p.patch_id)}
              style={{
                padding: '8px 10px', borderBottom: '1px solid #f3f4f6',
                cursor: 'pointer',
                background: selectedPatch?.patch_id === p.patch_id ? '#eff6ff' : 'transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 500 }}>{p.description}</span>
                <span style={{
                  fontSize: 11, padding: '1px 6px', borderRadius: 3,
                  color: '#fff', background: riskColor(p.risk_level),
                }}>
                  {p.risk_label}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
                {p.total_files} 个文件 · {p.total_lines} 行 · {p.status_label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Preview */}
      {previewLoading && (
        <p style={{ color: '#6b7280', fontSize: 13 }}>加载补丁预览中...</p>
      )}
      {selectedPatch && !previewLoading && (
        <div>
          <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>补丁预览</h3>

          {/* Summary */}
          <div style={{
            background: '#f9fafb', border: '1px solid #e5e7eb',
            borderRadius: 4, padding: '10px 12px', marginBottom: 12,
          }}>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}>
              <span>📄 <strong>{selectedPatch.total_files}</strong> 个文件</span>
              <span>📝 <strong>{selectedPatch.total_lines}</strong> 行变更</span>
              <span style={{ color: riskColor(selectedPatch.risk_level) }}>
                ⚠️ 风险：<strong>{selectedPatch.risk_label}</strong>
              </span>
            </div>
            <div style={{ marginTop: 8 }}>
              <p style={{ margin: 0, fontSize: 13 }}>{selectedPatch.description}</p>
            </div>
          </div>

          {/* File list */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={{ margin: '0 0 4px', fontSize: 12, fontWeight: 600, color: '#6b7280' }}>
              涉及文件
            </h4>
            {selectedPatch.files.map((f, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '4px 8px', fontSize: 12,
                background: i % 2 === 0 ? '#f9fafb' : 'transparent',
              }}>
                <code style={{ fontSize: 12 }}>{f.path}</code>
                <span style={{ color: f.operation === '删除' ? '#dc2626' : '#6b7280' }}>
                  {f.operation} ({f.hunk_count} hunks)
                </span>
              </div>
            ))}
          </div>

          {/* Diff preview */}
          {selectedPatch.unified_diff && (
            <div>
              <h4 style={{ margin: '0 0 4px', fontSize: 12, fontWeight: 600, color: '#6b7280' }}>
                Diff 预览
              </h4>
              <pre style={{
                background: '#1e293b', color: '#e2e8f0',
                padding: '10px 12px', borderRadius: 4,
                fontSize: 11, lineHeight: 1.5,
                maxHeight: 300, overflow: 'auto',
                whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              }}>
                {selectedPatch.unified_diff}
              </pre>
            </div>
          )}

          {/* Disclaimer */}
          <p style={{ color: '#9ca3af', fontSize: 11, marginTop: 12 }}>
            {selectedPatch.disclaimer || '此补丁仅用于预览，未应用到任何真实文件。'}
          </p>
        </div>
      )}
    </div>
  );
}
