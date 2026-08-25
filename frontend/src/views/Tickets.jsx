import React, { useEffect, useState } from 'react'
import {
  listTickets, getTicket, listUsers, assignTicket, setTicketStatus, suggestReply, setSatisfaction,
} from '../api.js'

const STATUS = [
  { key: 'pending', label: '待处理' },
  { key: 'processing', label: '处理中' },
  { key: 'resolved', label: '已解决' },
  { key: 'closed', label: '已关闭' },
]
const PRIORITY_LABEL = { low: '低', medium: '中', high: '高' }

export default function Tickets() {
  const [tickets, setTickets] = useState([])
  const [users, setUsers] = useState([])
  const [detail, setDetail] = useState(null)
  const [suggestion, setSuggestion] = useState('')
  const [suggestLoading, setSuggestLoading] = useState(false)

  async function reload() {
    const ts = await listTickets()
    setTickets(ts)
  }
  useEffect(() => {
    reload()
    listUsers().then(setUsers)
  }, [])

  const agents = users.filter(u => u.role === 'agent')

  async function open(id) {
    const d = await getTicket(id)
    setDetail(d)
    setSuggestion('')
  }

  async function doAssign(id, agentId) {
    await assignTicket(id, Number(agentId))
    await reload()
    await open(id)
  }
  async function doStatus(id, status) {
    await setTicketStatus(id, status)
    await reload()
    await open(id)
  }
  async function doSuggest(id) {
    setSuggestLoading(true)
    setSuggestion('')
    try {
      const r = await suggestReply(id)
      setSuggestion(r.suggestion)
    } finally { setSuggestLoading(false) }
  }
  async function doSatisfaction(id, val) {
    await setSatisfaction(id, val)
    await reload()
    await open(id)
  }

  return (
    <div>
      <div className="toolbar">
        <b>工单列表</b>
        <span className="hint">转人工的会话自动生成工单，含 AI 摘要与优先级</span>
        <span className="spacer" />
        <span className="hint">共 {tickets.length} 张工单</span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: detail ? '1.5fr 1fr' : '1fr', alignItems: 'start' }}>
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>#</th><th>标题 / 摘要</th><th>用户</th><th>优先级</th><th>状态</th>
                <th>负责人</th><th>满意度</th><th></th>
              </tr>
            </thead>
            <tbody>
              {tickets.map(t => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td style={{ maxWidth: 260 }}>
                    <div className="clickable" onClick={() => open(t.id)}><b>{t.title}</b></div>
                    <div className="small dim">{t.summary}</div>
                  </td>
                  <td>{t.user_name}</td>
                  <td><span className={`badge ${t.priority}`}>{PRIORITY_LABEL[t.priority] || t.priority}</span></td>
                  <td><span className={`badge ${t.status}`}>{STATUS.find(s => s.key === t.status)?.label || t.status}</span></td>
                  <td>{t.assignee_name || '—'}</td>
                  <td>{t.satisfaction ? t.satisfaction + ' 分' : '—'}</td>
                  <td><button className="btn sm" onClick={() => open(t.id)}>处理</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {detail && (
          <div className="card">
            <div className="section-title">工单 #{detail.id}</div>
            <div className="small dim">{detail.title}</div>
            <div className="mt">{detail.summary}</div>

            <div className="mt field">
              <label>分配客服</label>
              <select value={detail.assignee_id || ''} onChange={e => doAssign(detail.id, e.target.value)}>
                <option value="">未分配</option>
                {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>

            <div className="field">
              <label>状态流转</label>
              <div className="row" style={{ gap: 6 }}>
                {STATUS.map(s => (
                  <button key={s.key}
                    className={`btn sm ${detail.status === s.key ? 'primary' : ''}`}
                    onClick={() => doStatus(detail.id, s.key)}>{s.label}</button>
                ))}
              </div>
            </div>

            <div className="field">
              <button className="btn" onClick={() => doSuggest(detail.id)} disabled={suggestLoading}>
                {suggestLoading ? 'AI 生成中…' : '✨ AI 建议回复（知识库 + 历史相似工单）'}
              </button>
              {suggestion && <div className="card mt" style={{ background: '#f0f7ff' }}>{suggestion}</div>}
            </div>

            <div className="field">
              <label>解决后满意度评分</label>
              <div className="row" style={{ gap: 6 }}>
                {[1, 2, 3, 4, 5].map(v => (
                  <button key={v} className={`btn sm ${detail.satisfaction === v ? 'primary' : ''}`}
                    onClick={() => doSatisfaction(detail.id, v)}>{v} 分</button>
                ))}
              </div>
            </div>

            <div className="mt">
              <div className="section-title">对话历史</div>
              {(detail.history || []).map((m, i) => (
                <div key={i} className="small" style={{ padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
                  <b style={{ color: m.role === 'user' ? 'var(--primary)' : 'var(--good)' }}>{m.role === 'user' ? '用户' : 'AI'}:</b> {m.content}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
