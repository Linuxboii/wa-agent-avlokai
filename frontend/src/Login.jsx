import React, { useState } from 'react'
import { api, setToken } from './api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { token } = await api.login(username, password)
      setToken(token)
      onLogin()
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex items-center justify-center bg-gradient-to-br from-emerald-50 to-slate-100">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl p-8 w-80 space-y-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-800">AvlokAI</h1>
          <p className="text-sm text-slate-500">WhatsApp Console</p>
        </div>
        <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Username"
               value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Password"
               type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="text-red-500 text-xs">{error}</p>}
        <button disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
