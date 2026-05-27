import React, { useRef, useState, useEffect } from 'react'
import { Send, Image, Paperclip, X, FileText } from 'lucide-react'
import { api } from './api'

export default function Composer({ conversationId, onSent }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState(null) // { file, previewUrl, isImage }
  const imgRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => {
    return () => { if (pending?.previewUrl) URL.revokeObjectURL(pending.previewUrl) }
  }, [pending])

  const pickFile = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    const isImage = (file.type || '').startsWith('image/')
    setPending({
      file,
      isImage,
      previewUrl: isImage ? URL.createObjectURL(file) : null,
    })
  }

  const clearPending = () => {
    if (pending?.previewUrl) URL.revokeObjectURL(pending.previewUrl)
    setPending(null)
  }

  const send = async () => {
    if (busy) return
    if (pending) {
      setBusy(true)
      try {
        const m = await api.sendMedia(conversationId, pending.file, text.trim())
        onSent(m)
        clearPending()
        setText('')
      } finally { setBusy(false) }
      return
    }
    if (!text.trim()) return
    setBusy(true)
    try {
      const m = await api.sendText(conversationId, text.trim())
      onSent(m)
      setText('')
    } finally { setBusy(false) }
  }

  return (
    <div className="border-t bg-white">
      {pending && (
        <div className="p-3 border-b flex items-start gap-3">
          {pending.isImage ? (
            <img src={pending.previewUrl} alt="preview"
                 className="h-24 w-24 object-cover rounded-lg border" />
          ) : (
            <div className="h-24 w-24 flex flex-col items-center justify-center rounded-lg border bg-slate-50 text-slate-500 p-2">
              <FileText size={28} />
              <span className="text-[10px] mt-1 truncate w-full text-center">
                {pending.file.name}
              </span>
            </div>
          )}
          <div className="flex-1 text-sm text-slate-600">
            <div className="flex items-center justify-between">
              <span className="truncate font-medium">{pending.file.name}</span>
              <button onClick={clearPending} className="text-slate-400 hover:text-red-500">
                <X size={18} />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              {(pending.file.size / 1024).toFixed(0)} KB · add a caption below, then send
            </p>
          </div>
        </div>
      )}

      <div className="p-3 flex items-center gap-2">
        <input type="file" accept="image/*" ref={imgRef} hidden onChange={pickFile} />
        <input type="file" ref={fileRef} hidden onChange={pickFile} />
        <button onClick={() => imgRef.current?.click()} disabled={busy}
                className="p-2 text-slate-500 hover:text-emerald-600" title="Send image">
          <Image size={20} />
        </button>
        <button onClick={() => fileRef.current?.click()} disabled={busy}
                className="p-2 text-slate-500 hover:text-emerald-600" title="Send file">
          <Paperclip size={20} />
        </button>
        <input className="flex-1 border rounded-full px-4 py-2 text-sm"
               placeholder={pending ? 'Add a caption (optional)…' : 'Type a message…'}
               value={text}
               onChange={(e) => setText(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && send()} />
        <button onClick={send} disabled={busy}
                className="p-2 bg-emerald-600 text-white rounded-full hover:bg-emerald-700 disabled:opacity-50">
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
