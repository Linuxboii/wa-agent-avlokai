const API_BASE = 'https://wa-agent-avlokai.avlokai.com'
const TOKEN_KEY = 'avlok_wa_token'

export const mediaUrl = (path) =>
  path && path.startsWith('/') ? API_BASE + path : path

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function req(path, opts = {}) {
  const headers = opts.headers || {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(API_BASE + path, { ...opts, headers })
  if (res.status === 401) { clearToken(); window.location.reload() }
  if (!res.ok) throw new Error((await res.text()) || res.statusText)
  return res.status === 204 ? null : res.json()
}

export const api = {
  login: (username, password) =>
    fetch(API_BASE + '/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(async (r) => {
      if (!r.ok) throw new Error('Invalid credentials')
      return r.json()
    }),
  conversations: () => req('/api/conversations'),
  messages: (id) => req(`/api/conversations/${id}/messages`),
  sendText: (id, body) =>
    req(`/api/conversations/${id}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    }),
  sendMedia: (id, file, caption) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('caption', caption || '')
    return req(`/api/conversations/${id}/send-media`, { method: 'POST', body: fd })
  },
  pause: (id, paused) =>
    req(`/api/conversations/${id}/pause`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paused }),
    }),
  templates: () => req('/api/templates'),
  sendTemplate: (phone, template_name, language, body_params) =>
    req('/api/send-template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, template_name, language, body_params }),
    }),
  getSettings: () => req('/api/settings'),
  saveSettings: (system_prompt, openai_model) =>
    req('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system_prompt, openai_model }),
    }),
}

export function openSocket(onEvent) {
  const wsBase = API_BASE.replace(/^http/, 'ws')
  const ws = new WebSocket(`${wsBase}/ws`)
  ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token: getToken() }))
  ws.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)) } catch {}
  }
  return ws
}
