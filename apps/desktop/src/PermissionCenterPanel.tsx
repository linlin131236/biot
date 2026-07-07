/**
 * PermissionCenterPanel — 中文权限中心面板 (M92)。
 * 集中展示权限请求：风险等级、中文解释、操作内容、批准后影响。
 * 纯只读，不新增 approve/reject。现有审批只能走 PermissionGate 路径。
 * 不直接访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface PermissionItem {
  id: string;
  run_id: string;
  tool: string;
  tool_cn: string;
  operation: string;
  operation_cn: string;
  payload_summary: string;
  reason: string;
  status: string;
  status_cn: string;
  risk_level: string;
  risk_label_cn: string;
  risk_explanation_cn: string;
  impact_cn: string;
  action_cn: string;
}

interface PermissionSummary {
  items: PermissionItem[];
  total_pending: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  updated_at: string;
}

interface Props {
  baseUrl: string;
  api: {
    fetchPermissionCenter: (baseUrl: string) => Promise<Record<string, unknown>>;
  };
}

function mapSummary(raw: Record<string, unknown>): PermissionSummary {
  const items: PermissionItem[] = Array.isArray(raw.items)
    ? (raw.items as Record<string, unknown>[]).map((i: Record<string, unknown>) => ({
        id: (i.id as string) || '',
        run_id: (i.run_id as string) || '',
        tool: (i.tool as string) || '',
        tool_cn: (i.tool_cn as string) || '',
        operation: (i.operation as string) || '',
        operation_cn: (i.operation_cn as string) || '',
        payload_summary: (i.payload_summary as string) || '',
        reason: (i.reason as string) || '',
        status: (i.status as string) || '',
        status_cn: (i.status_cn as string) || '',
        risk_level: (i.risk_level as string) || '',
        risk_label_cn: (i.risk_label_cn as string) || '',
        risk_explanation_cn: (i.risk_explanation_cn as string) || '',
        impact_cn: (i.impact_cn as string) || '',
        action_cn: (i.action_cn as string) || '',
      }))
    : [];
  return {
    items,
    total_pending: (raw.total_pending as number) || 0,
    high_risk_count: (raw.high_risk_count as number) || 0,
    medium_risk_count: (raw.medium_risk_count as number) || 0,
    low_risk_count: (raw.low_risk_count as number) || 0,
    updated_at: (raw.updated_at as string) || '',
  };
}

export function PermissionCenterPanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<PermissionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterRisk, setFilterRisk] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchPermissionCenter(baseUrl);
        if (cancelled) return;
        setData(mapSummary(raw));
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="permissionCenterPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="permissionCenterPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="permissionCenterPanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const riskColor = (r: string) => r === 'high' ? '#d44' : r === 'medium' ? '#e90' : '#888';
  const filtered = filterRisk === 'all' ? data.items : data.items.filter(i => i.risk_level === filterRisk);

  return (
    <div className="permissionCenterPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>权限中心</h2>

      {/* Summary row */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <SummaryBadge label="待批准" value={data.total_pending} highlight={data.total_pending > 0} />
        <SummaryBadge label="高风险" value={data.high_risk_count} highlight={data.high_risk_count > 0} color="#d44" />
        <SummaryBadge label="中风险" value={data.medium_risk_count} highlight={false} color="#e90" />
        <SummaryBadge label="低风险" value={data.low_risk_count} highlight={false} color="#888" />
      </div>

      {/* Filter */}
      {data.items.length > 0 && (
        <div style={{ marginBottom: '0.5rem' }}>
          <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}
            style={{ padding: '2px 4px', fontSize: '0.8rem' }}>
            <option value="all">全部风险等级</option>
            <option value="high">高风险</option>
            <option value="medium">中风险</option>
            <option value="low">低风险</option>
          </select>
        </div>
      )}

      {/* Permission list */}
      {filtered.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>
          {data.total_pending === 0 ? '当前没有待处理的权限请求。' : '没有匹配的权限请求。'}
        </div>
      ) : (
        <div style={{ maxHeight: '30vh', overflowY: 'auto' }}>
          {filtered.map(item => (
            <div key={item.id} style={{
              padding: '6px 8px', margin: '3px 0', borderRadius: '3px',
              borderLeft: `3px solid ${riskColor(item.risk_level)}`,
              background: item.risk_level === 'high' ? '#fff5f5' : '#fafafa',
              fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>
                  <span style={{
                    padding: '1px 6px', borderRadius: '3px', fontSize: '0.7rem',
                    background: item.risk_level === 'high' ? '#fdd' : item.risk_level === 'medium' ? '#ffd' : '#efe',
                    marginRight: '6px',
                  }}>
                    {item.risk_label_cn}
                  </span>
                  <strong>{item.tool_cn}</strong>
                  <span style={{ color: '#666', marginLeft: '4px' }}>· {item.operation_cn}</span>
                </span>
                <span style={{ fontSize: '0.7rem', color: riskColor(item.risk_level) }}>
                  {item.status_cn}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '2px' }}>
                原因：{item.reason}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#999', marginTop: '2px' }}>
                {item.risk_explanation_cn}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#999' }}>
                批准后：{item.impact_cn}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px', fontStyle: 'italic' }}>
                {item.action_cn}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Read-only note */}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读权限展示。批准/拒绝操作请通过 PermissionGate 路径进行，本面板不提供自动批准。
      </div>
    </div>
  );
}

function SummaryBadge({ label, value, highlight, color }: { label: string; value: number; highlight: boolean; color?: string }) {
  return (
    <span style={{
      padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem',
      background: highlight ? '#fff0f0' : '#f0f4f0',
      border: `1px solid ${color || (highlight ? '#d88' : '#8c8')}`,
    }}>
      {label}：<strong>{value}</strong>
    </span>
  );
}
