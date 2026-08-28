import axios from 'axios'

const api = axios.create({ baseURL: '' })

export async function health() {
  const { data } = await api.get('/api/health')
  return data
}

export async function sendChat({ message, user_id, conversation_id }) {
  const { data } = await api.post('/api/chat', { message, user_id, conversation_id })
  return data
}

export async function getMessages(conversationId) {
  const { data } = await api.get(`/api/conversations/${conversationId}/messages`)
  return data
}

export async function sendFeedback({ message_id, conversation_id, kind }) {
  const { data } = await api.post('/api/feedback', { message_id, conversation_id, kind })
  return data
}

export async function getDashboard(start, end) {
  const params = {}
  if (start) params.start = start
  if (end) params.end = end
  const { data } = await api.get('/api/dashboard', { params })
  return data
}

// ---- 知识库 ----
export async function listDocs() {
  const { data } = await api.get('/api/kb/documents')
  return data
}
export async function getDoc(id) {
  const { data } = await api.get(`/api/kb/documents/${id}`)
  return data
}
export async function createDoc(payload) {
  const { data } = await api.post('/api/kb/documents', payload)
  return data
}
export async function updateDoc(id, payload) {
  const { data } = await api.put(`/api/kb/documents/${id}`, payload)
  return data
}
export async function deleteDoc(id) {
  const { data } = await api.delete(`/api/kb/documents/${id}`)
  return data
}
export async function restoreDoc(id, version) {
  const { data } = await api.post(`/api/kb/documents/${id}/restore?version=${version}`)
  return data
}

// ---- 工单 ----
export async function listTickets() {
  const { data } = await api.get('/api/tickets')
  return data
}
export async function getTicket(id) {
  const { data } = await api.get(`/api/tickets/${id}`)
  return data
}
export async function assignTicket(id, assignee_id) {
  const { data } = await api.put(`/api/tickets/${id}/assign`, { assignee_id })
  return data
}
export async function setTicketStatus(id, status) {
  const { data } = await api.put(`/api/tickets/${id}/status`, { status })
  return data
}
export async function suggestReply(id) {
  const { data } = await api.post(`/api/tickets/${id}/suggest`)
  return data
}
export async function setSatisfaction(id, satisfaction) {
  const { data } = await api.post(`/api/tickets/${id}/satisfaction`, { satisfaction })
  return data
}
export async function saveResolution(id, resolution) {
  const { data } = await api.put(`/api/tickets/${id}/resolution`, { resolution })
  return data
}

export async function listUsers() {
  const { data } = await api.get('/api/users')
  return data
}
