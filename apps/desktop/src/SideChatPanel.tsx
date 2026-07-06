/**
 * SideChatPanel — 长任务侧聊/指令补充面板。
 * M39: 用户可在当前 run 上追加中文指令，不自动执行 agent loop。
 * 不直接访问 fs/shell/process/ipcRenderer
 * 所有文案中文
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

export function SideChatPanel({ runId, api, baseUrl = 'http://core' }: SideChatPanelProps) {
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<'idle' | 'ok' | 'fail'>('idle');
  const canSend = !!runId && input.trim().length > 0;

  async function handleSend() {
    if (!runId || !input.trim()) return;
    try {
      await api.steerRun(baseUrl, runId, input.trim());
      setStatus('ok');
      setInput('');
    } catch {
      setStatus('fail');
    }
  }

  return <section className="sideChatPanel">
    <h2>侧聊 / 指令补充</h2>
    <input aria-label="侧聊内容" value={input} onChange={e => setInput(e.target.value)} />
    <button type="button" disabled={!canSend} onClick={handleSend}>发送指令</button>
    {!runId ? <span>暂无运行，无法发送</span> : null}
    {status === 'ok' ? <span>已加入当前任务</span> : null}
    {status === 'fail' ? <span>发送失败</span> : null}
  </section>;
}
