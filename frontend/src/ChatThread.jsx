import React, { useEffect, useRef } from 'react'
import { Mic, FileText, AlertCircle } from 'lucide-react'
import { mediaUrl } from './api'

function StatusTicks({ status }) {
  if (!status) return null
  if (status === 'failed') {
    return <AlertCircle size={12} className={'text-red-400 shrink-0'} title={'Failed'} />
  }
  const read = status === 'read'
  const delivered = status === 'delivered' || read
  const color = read ? '#53bdeb' : '#adb5bd'
  return (
    <svg width={16} height={11} viewBox={'0 0 16 11'} fill={'none'} title={status}
         className={'shrink-0 inline-block'}>
      <path d={'M1 5.5L4.5 9L10 3'} stroke={color} strokeWidth={1.7} strokeLinecap={'round'} strokeLinejoin={'round'} />
      {delivered && (
        <path d={'M5 5.5L8.5 9L14 3'} stroke={color} strokeWidth={1.7} strokeLinecap={'round'} strokeLinejoin={'round'} />
      )}
    </svg>
  )
}

function Bubble({ m }) {
  const out = m.direction === 'out'
  return (
    <div className={`flex ${out ? 'justify-end' : 'justify-start'} mb-2`}>
      <div className={`max-w-[70%] rounded-2xl px-3 py-2 text-sm ${
        out ? 'bg-emerald-600 text-white' : 'bg-white text-slate-800 border'}`}>
        {m.msg_type === 'image' && m.media_url && (
          <img src={mediaUrl(m.media_url)} alt={''} className={'rounded-lg mb-1 max-h-60'} />
        )}
        {m.msg_type === 'document' && m.media_url && (
          <a href={mediaUrl(m.media_url)} target={'_blank'} rel={'noreferrer'}
             className={'flex items-center gap-1 underline'}>
            <FileText size={14} /> {m.body || 'document'}
          </a>
        )}
        {m.msg_type === 'audio' && (
          <div className={'space-y-1'}>
            <div className={'flex items-center gap-1 opacity-70'}><Mic size={14} /> Voice note</div>
            {m.media_url && <audio controls src={mediaUrl(m.media_url)} className={'max-w-full'} />}
            {m.transcription && <p className={'italic'}>"{m.transcription}"</p>}
          </div>
        )}
        {m.msg_type === 'text' && <span>{m.body}</span>}
        {m.msg_type !== 'audio' && m.msg_type !== 'text' && m.body && (
          <p className={'mt-1'}>{m.body}</p>
        )}
        <div className={`flex items-center gap-1 justify-end text-[10px] mt-1 ${out ? 'text-emerald-100' : 'text-slate-400'}`}>
          <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          {out && <StatusTicks status={m.status} />}
        </div>
      </div>
    </div>
  )
}

export default function ChatThread({ messages }) {
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  return (
    <div className={'flex-1 overflow-y-auto p-4 bg-slate-50'}>
      {messages.map((m) => <Bubble key={m.id} m={m} />)}
      <div ref={end} />
    </div>
  )
}
