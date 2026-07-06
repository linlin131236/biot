/**
 * SideChatPanel — 长任务侧聊/指令补充面板。
 * M39: 用户可在当前 run 上追加中文指令，不自动执行 agent loop。
 * 不直接访问 fs/shell/process/ipcRenderer。
 * 所有文案中文。
 */
import { useState } from 'react';
import type { SteeringResult } from '@bolt/shared/autonomy';

interface SideChatPanelApi {
  steerRun: (baseUrl: string, runId: string, content: string) => Promise<SteeringResult>;
}

interface SideChatPanelProps {
  runId: string | null;
  api: SideChatPanelApi;
  baseUrl?: string;
}

interface ChatEntry { content: string; time: number; status: 'sent' | 'error' }

export function SideChatPanel({ runId, api, baseUrl = 'http://core' }: SideChatPanelProps) {
  const [input, setInput] = useState('');
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [error, setError] = useState('');
  const canSend = !!runId && input.trim().length > 0;

  async function handleSend() {
    if (!runId || !input.trim()) return;
    setError('');
    const content = input.trim();
    setInput('');
    try {
      await api.steerRun(baseUrl, runId, content);
      setEntries(prev => [...prev, { content, time: Date.now(), status: 'sent' }]);
    } catch { setError('发送失败'); setEntries(prev => [...prev, { content, time: Date.now(), status: 'error' }]); }
  }

  return <section className="sideChatPanel">
    <h2>侧聊指令</h2>
    {!runId ? <span>暂无运行，无法发送</span> : null}
    {error ? <span className="error">{error}</span> : null}
    <ul className="chatEntries">{entries.map((e, i) => <li key={i} className={e.status}>{e.content}</li>)}</ul>
    <input aria-label="侧聊内容" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && canSend && handleSend()} />
    <button type="button" disabled={!canSend} onClick={handleSend}>发送指令</button>
  </section>;
}
