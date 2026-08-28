import React, { useEffect, useRef, useState } from 'react'
import { sendChat, sendFeedback, listUsers, getMessages } from '../api.js'

export default function ChatView() {
  const [users, setUsers] = useState([])
  const [userId, setUserId] = useState(() => Number(localStorage.getItem('kefu_user_id')) || 1)
  const [conversationId, setConversationId] = useState(() => localStorage.getItem('kefu_conversation_id') || null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [feedback, setFeedback] = useState({}) // messageId -> 'up'|'down'
  const logRef = useRef(null)

  useEffect(() => {
    listUsers().then(us => {
      const customers = us.filter(u => u.role === 'customer')
      setUsers(customers)
      const savedUid = Number(localStorage.getItem('kefu_user_id'))
      if (customers.some(u => u.id === savedUid)) setUserId(savedUid)
      else if (customers.length) setUserId(customers[0].id)
    })
    // 恢复上次会话历史（切换页面不丢对话）
    const savedConv = localStorage.getItem('kefu_conversation_id')
    if (savedConv) {
      getMessages(Number(savedConv)).then(r => {
        if (r && r.messages && r.messages.length) {
          setMessages(r.messages.map(m => ({
            role: m.role, content: m.content, intent: m.intent,
            confidence: m.confidence, low_confidence: m.low_confidence,
            sources: m.sources || [], id: m.id,
          })))
          setConversationId(r.conversation_id)
        } else {
          localStorage.removeItem('kefu_conversation_id')
          setConversationId(null)
        }
      }).catch(() => {})
    }
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages])

  const append = (m) => setMessages(prev => [...prev, m])

  const persistConversation = (id) => {
    if (id) localStorage.setItem('kefu_conversation_id', String(id))
    else localStorage.removeItem('kefu_conversation_id')
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    append({ role: 'user', content: text })
    setSending(true)
    try {
      const r = await sendChat({ message: text, user_id: userId, conversation_id: conversationId })
      setConversationId(r.conversation_id)
      persistConversation(r.conversation_id)
      append({
        role: 'assistant',
        content: r.reply,
        intent: r.intent,
        confidence: r.confidence,
        low_confidence: r.low_confidence,
        transferred: r.transferred,
        sources: r.sources,
        message_id: 'pending',
        id: r.message_id,
      })
    } catch (e) {
      append({ role: 'assistant', content: '请求失败：' + (e?.message || '网络错误') })
    } finally {
      setSending(false)
    }
  }

  async function handleFeedback(m, kind) {
    if (!m.id) return
    setFeedback(prev => ({ ...prev, [m.id]: kind }))
    try {
      await sendFeedback({ message_id: m.id, conversation_id: conversationId, kind })
    } catch (e) { /* ignore */ }
  }

  return (
    <div className="chat-wrap">
      <div className="chat-head">
        <b>用户端 · 在线咨询</b>
        <span className="small dim">当前用户：</span>
        <select
          style={{ width: 180 }}
          value={userId}
          onChange={e => { const uid = Number(e.target.value); setUserId(uid); localStorage.setItem('kefu_user_id', String(uid)); setConversationId(null); persistConversation(null); setMessages([]); setFeedback({}) }}
        >
          {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <span className="spacer" />
        <button className="btn sm" onClick={() => { setConversationId(null); persistConversation(null); setMessages([]); setFeedback({}) }}>
          新会话
        </button>
      </div>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && (
          <div className="msg system">你好！我是「云作 Cloudwork」的 AI 客服，可以咨询套餐、发票、账号安全、故障排查等问题，也可以帮你查订单。</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
            {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
              <div className="sources">
                <div>📚 参考来源：</div>
                {m.sources.map((s, j) => (
                  <div key={j} className="source-item">
                    <b>{s.doc_title} · {s.source_ref}</b>（相似度 {s.score.toFixed(2)}）
                  </div>
                ))}
              </div>
            )}
            {m.low_confidence && (
              <div className="low-conf-banner">⚠️ 该问题置信度不足，已建议转人工，未使用知识库内容硬编答案。</div>
            )}
            {m.role === 'assistant' && m.id && m.intent === 'consult' && (
              <div className="feedback-row">
                <button
                  className={`feedback-btn ${feedback[m.id] === 'up' ? 'liked' : ''}`}
                  onClick={() => handleFeedback(m, 'up')}
                >👍 有用</button>
                <button
                  className={`feedback-btn ${feedback[m.id] === 'down' ? 'disliked' : ''}`}
                  onClick={() => handleFeedback(m, 'down')}
                >👎 没用</button>
              </div>
            )}
          </div>
        ))}
        {sending && <div className="msg system">AI 正在思考…</div>}
      </div>

      <div className="chat-input">
        <textarea
          value={input}
          placeholder="请输入你的问题，回车发送…"
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
          }}
        />
        <button className="btn primary" onClick={handleSend} disabled={sending}>发送</button>
      </div>
    </div>
  )
}
