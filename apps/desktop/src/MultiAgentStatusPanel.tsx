import { useEffect, useState } from 'react';
import type { MultiAgentRoleStatus, MultiAgentSubtask, AgentRole, SubtaskStatus } from '@bolt/shared/autonomy';

interface Props {
  baseUrl: string;
  api: {
    fetchRoles: (baseUrl: string) => Promise<Record<string, unknown>[]>;
    fetchBoard: (baseUrl: string) => Promise<Record<string, unknown>>;
    fetchSubtasks: (baseUrl: string, role?: string, status?: string) => Promise<Record<string, unknown>[]>;
  };
}

const ROLE_LABELS: Record<string, string> = {
  planner: '规划者',
  researcher: '研究员',
  builder: '构建者',
  reviewer: '审查者',
  skill_learner: '技能学习者',
};

export function MultiAgentStatusPanel({ baseUrl, api }: Props) {
  const [roles, setRoles] = useState<MultiAgentRoleStatus[]>([]);
  const [subtasks, setSubtasks] = useState<MultiAgentSubtask[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterRole, setFilterRole] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [rolesData, boardData, subtasksData] = await Promise.all([
          api.fetchRoles(baseUrl),
          api.fetchBoard(baseUrl),
          api.fetchSubtasks(baseUrl),
        ]);
        if (cancelled) return;
        const roleList: MultiAgentRoleStatus[] = Array.isArray(rolesData) ? rolesData.map((r: Record<string, unknown>) => ({
          role_id: (r.role_id as AgentRole) || 'builder',
          name_cn: (r.name_cn as string) || '',
          task_count: (r.task_count as number) || 0,
          blocked_count: (r.blocked_count as number) || 0,
        })) : [];
        setRoles(roleList);
        setSummary(boardData);
        const subtaskList: MultiAgentSubtask[] = Array.isArray(subtasksData) ? subtasksData.map((t: Record<string, unknown>) => ({
          task_id: (t.task_id as string) || '',
          title_cn: (t.title_cn as string) || '',
          assigned_role: (t.assigned_role as AgentRole) || 'builder',
          status: (t.status as SubtaskStatus) || 'pending',
          status_label_cn: (t.status_label_cn as string) || '',
          risk_level: (t.risk_level as string) || 'low',
          risk_label_cn: (t.risk_label_cn as string) || '',
          source_refs: Array.isArray(t.source_refs) ? t.source_refs as string[] : [],
        })) : [];
        setSubtasks(subtaskList);
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  const filtered = subtasks.filter(t => {
    if (filterRole !== 'all' && t.assigned_role !== filterRole) return false;
    if (filterStatus !== 'all' && t.status !== filterStatus) return false;
    return true;
  });

  const statusLabel = (s: string) => {
    const labels: Record<string, string> = {
      pending: '待办', ready: '就绪', in_progress: '进行中',
      blocked: '阻塞', awaiting_review: '待审查', completed: '已完成', failed: '已失败',
    };
    return labels[s] || s;
  };

  if (loading) return <div style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div style={{ padding: '1rem', color: '#c44' }}>{error}</div>;

  return (
    <div style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>多 Agent 状态</h3>

      {/* Role summary */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        {roles.length === 0 && <span style={{ color: '#888' }}>暂无角色数据</span>}
        {roles.map(r => (
          <span key={r.role_id} style={{
            padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem',
            background: r.blocked_count > 0 ? '#fff0f0' : '#f0f4f0',
            border: `1px solid ${r.blocked_count > 0 ? '#d88' : '#8c8'}`,
          }}>
            {ROLE_LABELS[r.role_id] || r.role_id}：{r.task_count} 任务{r.blocked_count > 0 ? `（${r.blocked_count} 阻塞）` : ''}
          </span>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <select value={filterRole} onChange={e => setFilterRole(e.target.value)}
          style={{ padding: '2px 4px', fontSize: '0.8rem' }}>
          <option value="all">全部角色</option>
          {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: '2px 4px', fontSize: '0.8rem' }}>
          <option value="all">全部状态</option>
          {['pending','ready','in_progress','blocked','awaiting_review','completed','failed'].map(s =>
            <option key={s} value={s}>{statusLabel(s)}</option>
          )}
        </select>
      </div>

      {/* Subtask list */}
      {filtered.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>暂无匹配的子任务。</div>
      ) : (
        <div style={{ maxHeight: '30vh', overflowY: 'auto' }}>
          {filtered.map(t => (
            <div key={t.task_id} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${t.status === 'blocked' ? '#d44' : t.status === 'completed' ? '#4a4' : '#aaa'}`,
              background: '#fafafa', fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{t.title_cn}</strong>
                <span style={{ fontSize: '0.7rem', color: '#666' }}>
                  {ROLE_LABELS[t.assigned_role] || t.assigned_role} · {statusLabel(t.status)}
                  {t.risk_level === 'high' || t.risk_level === 'critical' ? ` · ⚠${t.risk_label_cn}` : ''}
                </span>
              </div>
              {t.source_refs && t.source_refs.length > 0 && (
                <div style={{ fontSize: '0.65rem', color: '#999', marginTop: '2px' }}>
                  引用：{t.source_refs.slice(0, 3).join('、')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Read-only note */}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读状态展示，不提供执行、批准、删除功能。
      </div>
    </div>
  );
}
