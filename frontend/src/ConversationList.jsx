import React from 'react'
import { MessageSquare, PauseCircle, Plus } from 'lucide-react'

export default function ConversationList({ conversations, activeId, onSelect, onNew }) {
  return (
    <div className="w-72 border-r bg-white flex flex-col">
      <div className="p-3 border-b flex items-center justify-between">
        <span className="font-semibold text-slate-700">Conversations</span>
        <button onClick={onNew} title="Send template message"
          className="flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg px-2 py-1.5">
          <Plus size={14} /> New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 && (
          <p className="p-4 text-sm text-slate-400">No conversations yet.</p>
        )}
        {conversations.map((c) => (
          <button key={c.id} onClick={() => onSelect(c.id)}
            className={`w-full text-left px-4 py-3 border-b hover:bg-slate-50 ${
              activeId === c.id ? 'bg-emerald-50' : ''}`}>
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-800 truncate">
                {c.name || c.wa_id}
              </span>
              {c.ai_paused && <PauseCircle size={15} className="text-amber-500 shrink-0" />}
            </div>
            <div className="flex items-center gap-1 text-xs text-slate-500 truncate">
              <MessageSquare size={12} />
              <span className="truncate">
                {c.last_type && c.last_type !== 'text' ? `[${c.last_type}] ` : ''}
                {c.last_body || '…'}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
