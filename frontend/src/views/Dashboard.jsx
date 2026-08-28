import React, { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, PieChart, Pie, Cell, LineChart, Line,
} from 'recharts'
import { getDashboard } from '../api.js'

const CAT = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0d9488', '#db2777', '#0891b2']
const STATUS_COLOR = { pending: '#d97706', processing: '#2563eb', resolved: '#16a34a', closed: '#9ca3af' }
const STATUS_LABEL = { pending: '待处理', processing: '处理中', resolved: '已解决', closed: '已关闭' }

function todayStr(offset = 0) {
  const d = new Date()
  d.setDate(d.getDate() - offset)
  return d.toISOString().slice(0, 10)
}

function fmtSeconds(s) {
  if (!s) return '—'
  if (s < 60) return s.toFixed(1) + ' 秒'
  if (s < 3600) return (s / 60).toFixed(1) + ' 分钟'
  return (s / 3600).toFixed(1) + ' 小时'
}

export default function Dashboard() {
  const [start, setStart] = useState(todayStr(6))
  const [end, setEnd] = useState(todayStr(0))
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  async function load(s, e) {
    setLoading(true)
    setErr('')
    try {
      const d = await getDashboard(s, e)
      setData(d)
    } catch (e) {
      setErr('加载失败：' + (e?.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(start, end) }, [])

  function preset(days) {
    const e = todayStr(0)
    const s = todayStr(days - 1)
    setStart(s); setEnd(e)
    load(s, e)
  }

  const ticketStatusData = useMemo(() => {
    if (!data) return []
    return Object.entries(data.ticket_status || {}).map(([k, v]) => ({ name: STATUS_LABEL[k] || k, value: v }))
  }, [data])

  return (
    <div>
      {/* 筛选 */}
      <div className="toolbar">
        <label style={{ margin: 0 }}>开始</label>
        <input type="date" style={{ width: 160 }} value={start} onChange={e => setStart(e.target.value)} />
        <label style={{ margin: 0 }}>结束</label>
        <input type="date" style={{ width: 160 }} value={end} onChange={e => setEnd(e.target.value)} />
        <button className="btn primary" onClick={() => load(start, end)}>查询</button>
        <span className="hint">快捷：</span>
        <button className="btn sm" onClick={() => preset(1)}>今日</button>
        <button className="btn sm" onClick={() => preset(7)}>近7天</button>
        <button className="btn sm" onClick={() => preset(30)}>近30天</button>
        <span className="spacer" />
        {loading && <span className="small dim">加载中…（AI 聚类需要几秒）</span>}
      </div>

      {err && <div className="card mb" style={{ color: 'var(--serious)' }}>{err}</div>}
      {!data && !err && <div className="card mb dim">加载中…</div>}

      {data && (
        <>
          {/* 关键指标 */}
          <div className="grid stat-grid mb">
            <div className="card stat-tile">
              <div className="label">会话量（范围内）</div>
              <div className="value">{data.total_conversations}</div>
              <div className="sub">转人工 {data.transferred_count} 次</div>
            </div>
            <div className="card stat-tile">
              <div className="label">AI 解决率</div>
              <div className="value" style={{ color: 'var(--primary)' }}>{data.ai_resolution_rate}%</div>
              <div className="sub">AI 直接解决 {data.ai_resolved_count} 次</div>
            </div>
            <div className="card stat-tile">
              <div className="label">平均响应时长</div>
              <div className="value">{fmtSeconds(data.avg_response_seconds)}</div>
              <div className="sub">AI 首次响应</div>
            </div>
            <div className="card stat-tile">
              <div className="label">工单满意度</div>
              <div className="value">{data.ticket_avg_satisfaction ? data.ticket_avg_satisfaction.toFixed(1) + ' / 5' : '—'}</div>
              <div className="sub">点赞 {data.feedback.up} · 点踩 {data.feedback.down}</div>
            </div>
          </div>

          {/* 趋势 + 工单状态 */}
          <div className="grid" style={{ gridTemplateColumns: '2fr 1fr', alignItems: 'stretch' }}>
            <div className="card">
              <div className="section-title">会话量趋势</div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" name="会话量" fill="#2563eb" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="section-title">工单状态分布</div>
              {ticketStatusData.length ? (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={ticketStatusData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                        {ticketStatusData.map((entry, i) => (
                          <Cell key={i} fill={STATUS_COLOR[Object.keys(STATUS_COLOR).find(k => STATUS_LABEL[k] === entry.name)] || CAT[i % CAT.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="small dim">共 {data.ticket_total} 张工单</div>
                </>
              ) : <div className="dim">暂无工单</div>}
            </div>
          </div>

          {/* 满意度反馈（点赞/点踩 + 工单满意度，按时间范围可视化） */}
          <div className="grid mt" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'stretch' }}>
            <div className="card">
              <div className="section-title">👍 点赞 / 点踩反馈（按天）</div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.feedback_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="up" name="点赞" fill="#16a34a" radius={[4, 4, 0, 0]} maxBarSize={24} />
                  <Bar dataKey="down" name="点踩" fill="#dc2626" radius={[4, 4, 0, 0]} maxBarSize={24} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="section-title">⭐ 工单满意度评分（按天）</div>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={data.satisfaction_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 5]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" name="满意度" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 热门问题 + 缺口分析 */}
          <div className="grid mt" style={{ gridTemplateColumns: '1fr 1.6fr', alignItems: 'start' }}>
            <div className="card">
              <div className="section-title">🔥 热门问题 Top10（AI 聚类）</div>
              {data.hot_topics.length === 0 && <div className="dim">范围内暂无对话</div>}
              {data.hot_topics.slice(0, 10).map((t, i) => (
                <div key={i} className="row" style={{ padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
                  <span className="badge medium" style={{ width: 26, textAlign: 'center' }}>{i + 1}</span>
                  <span style={{ fontWeight: 600 }}>{t.label}</span>
                  <span className="small dim">例：{t.examples[0]?.slice(0, 22)}…</span>
                  <span className="spacer" />
                  <b>{t.count}</b>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="section-title">📌 知识库缺口分析（转人工问题反推）</div>
              {data.gap_analysis.length === 0 && <div className="dim">范围内暂无转人工问题</div>}
              {data.gap_analysis.map((g, i) => (
                <div key={i} className="card" style={{ border: '1px solid #fde68a', background: '#fffbeb', marginBottom: 10, padding: 12 }}>
                  <div className="row">
                    <b>{g.label}</b>
                    <span className="badge high">{g.count} 条 · {g.pct}%</span>
                  </div>
                  <div className="small" style={{ marginTop: 6 }}>{g.suggestion}</div>
                  <div className="small dim" style={{ marginTop: 4 }}>示例：{g.examples.join(' / ')}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
