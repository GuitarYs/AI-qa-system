import React, { useEffect, useRef, useState } from 'react'
import { listDocs, getDoc, createDoc, updateDoc, deleteDoc, restoreDoc } from '../api.js'

const EMPTY = { title: '', category: 'FAQ', content: '' }

export default function KnowledgeBase() {
  const [docs, setDocs] = useState([])
  const [editing, setEditing] = useState(null)   // {id?, title, category, content}
  const [versions, setVersions] = useState([])
  const [detail, setDetail] = useState(null)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef(null)

  async function reload() {
    const ds = await listDocs()
    setDocs(ds)
  }
  useEffect(() => { reload() }, [])

  function startNew() { setEditing({ ...EMPTY }); setDetail(null); setVersions([]) }

  async function startEdit(d) {
    const full = await getDoc(d.id)
    setEditing({ id: full.id, title: full.title, category: full.category, content: full.content })
    setVersions(full.versions || [])
    setDetail(full)
  }

  async function save() {
    if (!editing.title.trim() || !editing.content.trim()) { alert('标题与内容不能为空'); return }
    setBusy(true)
    try {
      if (editing.id) {
        await updateDoc(editing.id, { title: editing.title, category: editing.category, content: editing.content, note: '手动更新' })
      } else {
        await createDoc({ title: editing.title, category: editing.category, content: editing.content, note: '新建' })
      }
      setEditing(null); setVersions([]); setDetail(null)
      await reload()
    } finally { setBusy(false) }
  }

  async function remove(d) {
    if (!confirm(`确定删除文档「${d.title}」？`)) return
    await deleteDoc(d.id)
    await reload()
  }

  async function restore(d, v) {
    if (!confirm(`确定回滚「${d.title}」到版本 v${v.version}？（会新增一个版本）`)) return
    setBusy(true)
    try {
      await restoreDoc(d.id, v.version)
      await reload()
      setEditing(null); setVersions([]); setDetail(null)
    } finally { setBusy(false) }
  }

  async function upload(e) {
    const file = e.target.files[0]
    if (!file) return
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('category', 'FAQ')
      await fetch('/api/kb/upload', { method: 'POST', body: form })
      await reload()
    } finally { setBusy(false); e.target.value = '' }
  }

  return (
    <div>
      <div className="toolbar">
        <button className="btn primary" onClick={startNew}>+ 新建文档</button>
        <button className="btn" onClick={() => fileRef.current?.click()}>上传文件（.md / .txt）</button>
        <input ref={fileRef} type="file" accept=".md,.txt,.markdown" style={{ display: 'none' }} onChange={upload} />
        <span className="spacer" />
        <span className="hint">共 {docs.length} 篇文档 · 上传后自动分块、向量化入库</span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: editing ? '1.4fr 1fr' : '1fr', alignItems: 'start' }}>
        <div className="card">
          <table className="table">
            <thead>
              <tr><th>标题</th><th>分类</th><th>版本</th><th>分块</th><th>更新时间</th><th>操作</th></tr>
            </thead>
            <tbody>
              {docs.map(d => (
                <tr key={d.id}>
                  <td><b>{d.title}</b></td>
                  <td>{d.category}</td>
                  <td>v{d.current_version}</td>
                  <td>{d.chunk_count}</td>
                  <td className="small dim">{(d.updated_at || d.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                  <td className="row" style={{ gap: 6 }}>
                    <button className="btn sm" onClick={() => startEdit(d)}>编辑</button>
                    <button className="btn sm" onClick={() => getDoc(d.id).then(f => { setDetail(f); setVersions(f.versions || []); setEditing(null) })}>版本</button>
                    <button className="btn sm danger" onClick={() => remove(d)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 编辑 / 版本面板 */}
        {editing && (
          <div className="card">
            <div className="section-title">{editing.id ? `编辑：${editing.title}` : '新建文档'}</div>
            <div className="field">
              <label>标题</label>
              <input value={editing.title} onChange={e => setEditing({ ...editing, title: e.target.value })} />
            </div>
            <div className="field">
              <label>分类</label>
              <select value={editing.category} onChange={e => setEditing({ ...editing, category: e.target.value })}>
                <option>FAQ</option><option>退换货政策</option><option>产品手册</option><option>其他</option>
              </select>
            </div>
            <div className="field">
              <label>内容（Markdown，支持 Q1：… 问答格式）</label>
              <textarea style={{ minHeight: 260 }} value={editing.content}
                onChange={e => setEditing({ ...editing, content: e.target.value })} />
            </div>
            <div className="row">
              <button className="btn primary" onClick={save} disabled={busy}>{busy ? '保存中…' : '保存（生成新版本）'}</button>
              <button className="btn" onClick={() => { setEditing(null); setVersions([]) }}>取消</button>
            </div>
            {versions.length > 0 && (
              <div className="mt">
                <div className="section-title">版本历史</div>
                {versions.map(v => (
                  <div key={v.version} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <b>v{v.version}</b>
                    <span className="small dim">{v.note} · {(v.created_at || '').slice(0, 16).replace('T', ' ')}</span>
                    <span className="spacer" />
                    <button className="btn sm" onClick={() => restore(detail, v)}>回滚到此版本</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!editing && detail && (
          <div className="card">
            <div className="section-title">{detail.title} · 版本历史</div>
            {versions.map(v => (
              <div key={v.version} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                <b>v{v.version}</b>
                <span className="small dim">{v.note} · {(v.created_at || '').slice(0, 16).replace('T', ' ')}</span>
                <span className="spacer" />
                <button className="btn sm" onClick={() => restore(detail, v)}>回滚</button>
              </div>
            ))}
            <div className="mt small dim">共 {versions.length} 个版本，可追溯到历史内容。</div>
          </div>
        )}
      </div>
    </div>
  )
}
