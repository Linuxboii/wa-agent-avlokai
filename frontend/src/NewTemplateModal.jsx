import React, { useEffect, useMemo, useState } from 'react'
import { X, Send } from 'lucide-react'
import { api } from './api'

function bodyText(t) {
  const c = (t.components || []).find((x) => x.type === 'BODY')
  return c?.text || ''
}

function paramCount(t) {
  const matches = bodyText(t).match(/\{\{\d+\}\}/g) || []
  return new Set(matches).size
}

export default function NewTemplateModal({ onClose, onSent }) {
  const [phone, setPhone] = useState('')
  const [templates, setTemplates] = useState([])
  const [selected, setSelected] = useState('')
  const [params, setParams] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.templates()
      .then(setTemplates)
      .catch(() => setError('Could not load templates. Check WhatsApp credentials.'))
  }, [])

  const current = useMemo(
    () => templates.find((t) => `${t.name}|${t.language}` === selected),
    [templates, selected]
  )
  const nParams = current ? paramCount(current) : 0

  useEffect(() => { setParams(Array(nParams).fill('')) }, [selected, nParams])

  const send = async () => {
    setError('')
    if (!phone.trim()) return setError('Enter a phone number')
    if (!current) return setError('Pick a template')
    if (params.some((p) => !p.trim())) return setError('Fill all template variables')
    setBusy(true)
    try {
      const res = await api.sendTemplate(
        phone.trim(), current.name, current.language, nParams ? params : null
      )
      onSent(res.conversation_id)
      onClose()
    } catch (e) {
      setError(String(e.message || 'Send failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-20">
      <div className="w-96 bg-white rounded-2xl shadow-xl p-5 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-slate-800">Send template message</h2>
          <button onClick={onClose}><X size={20} className="text-slate-500" /></button>
        </div>

        <div>
          <label className="text-xs text-slate-500">Phone number (with country code)</label>
          <input className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                 placeholder="e.g. 919876543210" value={phone}
                 onChange={(e) => setPhone(e.target.value)} autoFocus />
        </div>

        <div>
          <label className="text-xs text-slate-500">Template</label>
          <select className="w-full border rounded-lg px-3 py-2 text-sm mt-1 bg-white"
                  value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">— choose a template —</option>
            {templates.map((t) => (
              <option key={`${t.name}|${t.language}`} value={`${t.name}|${t.language}`}>
                {t.name} ({t.language})
              </option>
            ))}
          </select>
        </div>

        {current && bodyText(current) && (
          <p className="text-xs text-slate-500 bg-slate-50 rounded-lg p-2 whitespace-pre-wrap">
            {bodyText(current)}
          </p>
        )}

        {Array.from({ length: nParams }).map((_, i) => (
          <input key={i} className="w-full border rounded-lg px-3 py-2 text-sm"
                 placeholder={`Variable {{${i + 1}}}`} value={params[i] || ''}
                 onChange={(e) => {
                   const next = [...params]; next[i] = e.target.value; setParams(next)
                 }} />
        ))}

        {error && <p className="text-red-500 text-xs">{error}</p>}

        <button onClick={send} disabled={busy}
                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          <Send size={16} /> {busy ? 'Sending…' : 'Send template'}
        </button>
      </div>
    </div>
  )
}
