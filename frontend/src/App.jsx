import React, { useEffect, useState } from 'react'
import ChatView from './views/ChatView.jsx'
import AdminView from './views/AdminView.jsx'

function useHashRoute() {
  const [route, setRoute] = useState(window.location.hash || '#/')
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash || '#/')
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  return route
}

export default function App() {
  const route = useHashRoute()
  const isAdmin = route.startsWith('#/admin')

  return (
    <div>
      <div className="topbar">
        <span className="brand">云作 Cloudwork <span className="dot">·</span> AI 客服系统</span>
        <span className="small dim">全栈客服 · RAG + LLM</span>
        <span className="spacer" />
        <button
          className={`nav-btn ${!isAdmin ? 'active' : ''}`}
          onClick={() => { window.location.hash = '#/' }}
        >用户端</button>
        <button
          className={`nav-btn ${isAdmin ? 'active' : ''}`}
          onClick={() => { window.location.hash = '#/admin' }}
        >管理后台</button>
      </div>
      {isAdmin ? <AdminView /> : <ChatView />}
    </div>
  )
}
