import { useMemo, useState } from 'react';

export type DiagnosticsFeedbackApi = {
  exportSummary: () => Promise<string>;
  openDiagnosticsDir: () => Promise<void>;
  setCollectionEnabled: (enabled: boolean) => Promise<void>;
  getCollectionEnabled: () => Promise<boolean>;
};

export function DiagnosticsFeedbackPanel({ api }: { api: DiagnosticsFeedbackApi }) {
  const [summary, setSummary] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useMemo(() => {
    void api.getCollectionEnabled().then(setEnabled).catch(() => setEnabled(true));
  }, [api]);

  async function refresh() {
    try {
      setError('');
      setSummary(await api.exportSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法读取诊断信息');
    }
  }

  async function copySummary() {
    const text = summary || (await api.exportSummary());
    setSummary(text);
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    }
    setCopied(true);
  }

  async function toggleCollection() {
    const next = !enabled;
    await api.setCollectionEnabled(next);
    setEnabled(next);
  }

  return (
    <section className="diagnosticsFeedbackPanel" style={{ padding: '0.75rem' }}>
      <h2>诊断与反馈</h2>
      <p>诊断信息默认仅保存在本机。上传需要你主动同意；当前版本不自动上传。</p>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <button type="button" onClick={() => void refresh()}>刷新脱敏诊断</button>
        <button type="button" onClick={() => void copySummary()}>复制脱敏诊断信息</button>
        <button type="button" onClick={() => void api.openDiagnosticsDir()}>打开日志目录</button>
        <button type="button" onClick={() => void toggleCollection()}>
          {enabled ? '关闭崩溃收集' : '开启崩溃收集'}
        </button>
      </div>
      {copied ? <p>已复制到剪贴板（如浏览器权限允许）。</p> : null}
      {error ? <p style={{ color: '#c44' }}>{error}</p> : null}
      <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>{summary || '尚未加载诊断摘要。'}</pre>
    </section>
  );
}
