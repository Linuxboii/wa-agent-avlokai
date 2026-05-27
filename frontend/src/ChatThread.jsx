import React, { useEffect, useRef } from 'react'
import { Mic, FileText } from 'lucide-react'
import { mediaUrl } from './api'

function Bubble({ m }) {
  const out = m.direction === 'out'
  return (
    <div className={`flex ${out ? 'justify-end' : 'justify-start'} mb-2`}>
      <div className={`max-w-[70%] rounded-2xl px-3 py-2 text-sm ${
        out ? 'bg-emerald-600 text-white' : 'bg-white text-slate-800 border'}`}>
        {m.msg_type === 'image' && m.media_url && (
          <img src={mediaUrl(m.media_url)} alt="" className="rounded-lg mb-1 max-h-60" />
        )}
        {m.msg_type === 'document' && m.media_url && (
          <a href={mediaUrl(m.media_url)} target="_blank" rel="noreferrer"
             className="flex items-center gap-1 underline">
            <FileText size={14} /> {m.body || 'document'}
          </a>
        )}
        {m.msg_type === 'audio' && (
          <div className="space-y-1">
            <div className="flex items-center gap-1 opacity-70"><Mic size={14} /> Voice note</div>
            {m.media_url && <audio controls src={mediaUrl(m.media_url)} className="max-w-full" />}
            {m.transcription && <p className="italic">“{m.transcription}”</p>}
          </div>
        )}
        {m.msg_type === 'text' && <span>{m.body}</span>}
        {m.msg_type !== 'audio' && m.msg_type !== 'text' && m.body && (
          <p className="mt-1">{m.body}</p>
        )}
        <div className={`text-[10px] mt-1 ${out ? 'text-emerald-100' : 'text-slate-400'}`}>
          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

export default function ChatThread({ messages }) {
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  return (
    <div className="flex-1 overflow-y-auto p-4 bg-slate-50">
      {messages.map((m) => <Bubble key={m.id} m={m} />)}
      <div ref={end} />
    </div>
  )
}
