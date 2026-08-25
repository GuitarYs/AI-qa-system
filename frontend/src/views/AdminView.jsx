import React, { useState } from 'react'
import Dashboard from './Dashboard.jsx'
import KnowledgeBase from './KnowledgeBase.jsx'
import Tickets from './Tickets.jsx'

const TABS = [
  { key: 'dashboard', label: '数据分析看板' },
  { key: 'kb', label: '知识库管理' },
  { key: 'tickets', label: '工单系统' },
]

export default function AdminView() {
  const [tab, setTab] = useState('dashboard')

  return (
    <div className="page">
      <div className="tabs">
        {TABS.map(t => (
          <button key={t.key} className={`tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'dashboard' && <Dashboard />}
      {tab === 'kb' && <KnowledgeBase />}
      {tab === 'tickets' && <Tickets />}
    </div>
  )
}
