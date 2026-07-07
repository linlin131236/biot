/**
 * MemorySearchPanel — 只读记忆搜索面板。
 * M79: 搜索决策、失败、偏好、项目画像、代码地图。
 * 中文 UI、只读、不暴露 ipcRenderer/fs/shell/process。
 * 不提供写入/删除/执行按钮。
 */
import { useState, useCallback } from 'react';
import type { MemorySearchResult, MemorySearchCategory } from '@bolt/shared/autonomy';

interface MemorySearchApi {
  fetchDecisions: (baseUrl: string, keyword: string) => Promise<Record<string, unknown>[]>;
  fetchFailures: (baseUrl: string, keyword: string) => Promise<Record<string, unknown>[]>;
  fetchPreferences: (baseUrl: string, keyword: string) => Promise<Record<string, unknown>[]>;
  fetchProfile: (baseUrl: string) => Promise<Record<string, unknown>>;
  fetchCodeMap: (baseUrl: string, keyword: string) => Promise<Record<string, unknown>[]>;
}

interface MemorySearchPanelProps {
  baseUrl?: string;
  api: MemorySearchApi;
}

const CATEGORY_TABS: { key: MemorySearchCategory; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'decision', label: '决策' },
  { key: 'failure', label: '失败' },
  { key: 'preference', label: '偏好' },
  { key: 'project', label: '项目' },
  { key: 'code_map', label: '代码地图' },
];

function mapResults(
  items: Record<string, unknown>[],
  type: MemorySearchCategory,
  idField: string,
  titleField: string,
  summaryField: string,
): MemorySearchResult[] {
  return items.map((item: Record<string, unknown>) => ({
    type,
    id: String(item[idField] ?? ''),
    title_cn: String(item[titleField] ?? ''),
    summary_cn: String(item[summaryField] ?? ''),
    source_refs: Array.isArray(item.source_refs) ? item.source_refs as string[] : [],
    risk_label: type === 'failure' ? String(item.severity ?? '') : undefined,
  }));
}

export function MemorySearchPanel({ baseUrl = 'http://core', api }: MemorySearchPanelProps) {
  const [keyword, setKeyword] = useState('');
  const [activeTab, setActiveTab] = useState<MemorySearchCategory>('all');
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');

  const doSearch = useCallback(async () => {
    const kw = keyword.trim();
    if (!kw) return;
    setSearching(true);
    setError('');
    setSearched(true);
    const all: MemorySearchResult[] = [];

    try {
      if (activeTab === 'all' || activeTab === 'decision') {
        const items = await api.fetchDecisions(baseUrl, kw);
        all.push(...mapResults(items, 'decision', 'decision_id', 'title', 'summary_cn'));
      }
      if (activeTab === 'all' || activeTab === 'failure') {
        const items = await api.fetchFailures(baseUrl, kw);
        all.push(...mapResults(items, 'failure', 'failure_id', 'symptom_cn', 'fix_summary_cn'));
      }
      if (activeTab === 'all' || activeTab === 'preference') {
        const items = await api.fetchPreferences(baseUrl, kw);
        all.push(...mapResults(items, 'preference', 'preference_id', 'statement_cn', 'statement_cn'));
      }
      if (activeTab === 'all' || activeTab === 'code_map') {
        const items = await api.fetchCodeMap(baseUrl, kw);
        all.push(...mapResults(items, 'code_map', 'entry_id', 'file_path', 'summary'));
      }
      if (activeTab === 'all' || activeTab === 'project') {
        try {
          const profile = await api.fetchProfile(baseUrl);
          if (profile && typeof profile === 'object') {
            const profileText = JSON.stringify(profile).toLowerCase();
            if (profileText.includes(kw.toLowerCase())) {
              all.push({
                type: 'project',
                id: 'project-profile',
                title_cn: String(profile.project_name ?? '项目画像'),
                summary_cn: `Milestone: ${profile.current_milestone ?? '?'} | Tech: ${JSON.stringify(profile.tech_stack ?? {})}`,
                source_refs: Array.isArray(profile.source_refs) ? profile.source_refs as string[] : [],
              });
            }
          }
        } catch { /* project profile not available */ }
      }
      setResults(all);
    } catch (e) {
      setError('搜索失败，请检查 Agent Core 连接');
    } finally {
      setSearching(false);
    }
  }, [keyword, activeTab, baseUrl, api]);

  const filteredResults = activeTab === 'all'
    ? results
    : results.filter(r => r.type === activeTab);

  return (
    <section className="memorySearchPanel">
      <h2>记忆搜索</h2>

      <div className="memorySearchTabs">
        {CATEGORY_TABS.map(tab => (
          <button
            key={tab.key}
            type="button"
            className={activeTab === tab.key ? 'active' : ''}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="memorySearchInput">
        <input
          aria-label="搜索记忆"
          placeholder="输入关键词搜索记忆..."
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') doSearch(); }}
        />
        <button type="button" disabled={!keyword.trim() || searching} onClick={doSearch}>
          {searching ? '搜索中...' : '搜索'}
        </button>
      </div>

      {error && <span className="error">{error}</span>}

      {searched && !searching && filteredResults.length === 0 && !error && (
        <div className="memorySearchEmpty">未找到匹配的记忆记录，试试其他关键词。</div>
      )}

      {filteredResults.length > 0 && (
        <ul className="memorySearchResults">
          {filteredResults.map((r, i) => (
            <li key={`${r.type}-${r.id}-${i}`} className="memorySearchResultItem">
              <div className="memorySearchResultHeader">
                <span className="memorySearchResultType">
                  {CATEGORY_TABS.find(t => t.key === r.type)?.label ?? r.type}
                </span>
                {r.risk_label && (
                  <span className={`memorySearchRisk memorySearchRisk${r.risk_label.toLowerCase()}`}>
                    严重度: {r.risk_label}
                  </span>
                )}
              </div>
              <div className="memorySearchResultTitle">{r.title_cn}</div>
              <div className="memorySearchResultSummary">{r.summary_cn}</div>
              {r.source_refs.length > 0 && (
                <div className="memorySearchResultRefs">
                  来源: {r.source_refs.slice(0, 3).join(', ')}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="memorySearchNote">
        此面板为只读搜索，不提供写入、删除、执行功能。敏感记忆不在此展示。
      </div>
    </section>
  );
}
