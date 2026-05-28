import React, { useEffect, useMemo, useState } from 'react'
import { X, Send } from 'lucide-react'
import { api } from './api'

const DEFAULT_HEADER_IMAGE = 'https://www.avlokai.com/api/whatsapp-brochure'

function bodyText(t) {
  const c = (t.components || []).find((x) => x.type === 'BODY')
  return c?.text || ''
}

function footerText(t) {
  const c = (t.components || []).find((x) => x.type === 'FOOTER')
  return c?.text || ''
}

function paramCount(t) {
  const matches = bodyText(t).match(/\{\{\d+\}\}/g) || []
  return new Set(matches).size
}

function hasImageHeader(t) {
  return (t.components || []).some(
    (x) => x.type === 'HEADER' && x.format === 'IMAGE'
  )
}

function resolveBody(text, params) {
  return text.replace(/\{\{(\d+)\}\}/g, (_, n) => params[Number(n) - 1] || `{{${n}}}`)
}

function isPreviewReady(current, params, headerImageUrl) {
  if (!current) return false
  if (hasImageHeader(current) && !headerImageUrl.trim()) return false
  if (params.some((p) => !p.trim())) return false
  return true
}

export default function NewTemplateModal({ onClose, onSent }) {
  const [phone, setPhone] = useState('')
  const [templates, setTemplates] = useState([])
  const [selected, setSelected] = useState('')
  const [params, setParams] = useState([])
  const [headerImageUrl, setHeaderImageUrl] = useState('')
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

  useEffect(() => {
    setParams(Array(nParams).fill(''))
    setHeaderImageUrl(DEFAULT_HEADER_IMAGE)
  }, [selected, nParams])

  const previewReady = isPreviewReady(current, params, headerImageUrl)

  const send = async () => {
    setError('')
    if (!phone.trim()) return setError('Enter a phone number')
    if (!current) return setError('Pick a template')
    if (hasImageHeader(current) && !headerImageUrl.trim()) return setError('Enter a header image URL')
    if (params.some((p) => !p.trim())) return setError('Fill all template variables')
    setBusy(true)
    try {
      const res = await api.sendTemplate(
        phone.trim(), current.name, current.language,
        nParams ? params : null,
        hasImageHeader(current) ? headerImageUrl.trim() : null
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
      <div className="w-[28rem] bg-white rounded-2xl shadow-xl p-5 space-y-4 max-h-[90vh] overflow-y-auto">
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

        {current && hasImageHeader(current) && (
          <div>
            <label className="text-xs text-slate-500">Header image URL</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                   placeholder={DEFAULT_HEADER_IMAGE}
                   value={headerImageUrl}
                   onChange={(e) => setHeaderImageUrl(e.target.value)} />
          </div>
        )}

        {Array.from({ length: nParams }).map((_, i) => (
          <input key={i} className="w-full border rounded-lg px-3 py-2 text-sm"
                 placeholder={`Variable {{${i + 1}}}`} value={params[i] || ''}
                 onChange={(e) => {
                   const next = [...params]; next[i] = e.target.value; setParams(next)
                 }} />
        ))}

        {current && previewReady && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Preview</p>
            <div className="bg-[#e9fbe5] rounded-xl rounded-tl-none p-3 space-y-2 shadow-sm max-w-xs mx-auto">
              {hasImageHeader(current) && (
                <img
                  src={headerImageUrl}
                  alt="Header"
                  className="w-full rounded-lg object-cover max-h-40"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              )}
              {bodyText(current) && (
                <p className="text-sm text-slate-800 whitespace-pre-wrap">
                  {resolveBody(bodyText(current), params)}
                </p>
              )}
              {footerText(current) && (
                <p className="text-xs text-slate-400">{footerText(current)}</p>
              )}
            </div>
          </div>
        )}

        {error && <p className="text-red-500 text-xs">{error}</p>}

        <button onClick={send} disabled={busy}
                className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          <Send size={16} /> {busy ? 'Sending…' : 'Send template'}
        </button>
      </div>
    </div>
  )
}
