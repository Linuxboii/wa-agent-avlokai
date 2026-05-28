import React, { useEffect, useState, useRef, useCallback } from 'react'
import { Settings, LogOut, Bot, BotOff, Phone, Copy, Check } from 'lucide-react'
import { api, clearToken, openSocket } from './api'
import ConversationList from './ConversationList'
import ChatThread from './ChatThread'
import Composer from './Composer'
import SettingsPanel from './SettingsPanel'
import NewTemplateModal from './NewTemplateModal'

export default function Dashboard({ onLogout }) {
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [showSettings, setShowSettings] = useState(false)
  const [showTemplate, setShowTemplate] = useState(false)
  const [copiedPhoneFor, setCopiedPhoneFor] = useState(null)
  const activeRef = useRef(null)
  activeRef.current = activeId

  const refreshConversations = useCallback(() => {
    api.conversations().then(setConversations).catch(() => {})
  }, [])

  useEffect(() => { refreshConversations() }, [refreshConversations])

  useEffect(() => {
    if (activeId == null) return
    api.messages(activeId).then(setMessages).catch(() => {})
  }, [activeId])

  useEffect(() => {
    const ws = openSocket((evt) => {
      if (evt.event === 'message') {
        refreshConversations()
        if (evt.data.conversation_id === activeRef.current) {
          setMessages((prev) =>
            prev.some((m) => m.id === evt.data.id) ? prev : [...prev, evt.data])
        }
      } else if (evt.event === 'status_update') {
        if (evt.data.conversation_id === activeRef.current) {
          setMessages((prev) => prev.map((m) =>
            m.id === evt.data.message_id ? { ...m, status: evt.data.status } : m))
        }
      } else if (evt.event === 'pause') {
        refreshConversations()
      }
    })
    return () => ws.close()
  }, [refreshConversations])

  const active = conversations.find((c) => c.id === activeId)

  const togglePause = async () => {
    if (!active) return
    await api.pause(active.id, !active.ai_paused)
    refreshConversations()
  }

  const copyPhone = async () => {
    if (!active?.wa_id) return
    await navigator.clipboard.writeText(active.wa_id)
    setCopiedPhoneFor(active.id)
    window.setTimeout(() => setCopiedPhoneFor(null), 1500)
  }

  const logout = () => { clearToken(); onLogout() }
  const onSent = (m) =>
    setMessages((prev) => (prev.some((x) => x.id === m.id) ? prev : [...prev, m]))

  return (
    <div className="h-full flex relative">
      <ConversationList conversations={conversations} activeId={activeId}
                        onSelect={setActiveId} onNew={() => setShowTemplate(true)} />
      <div className="flex-1 flex flex-col">
        <div className="h-14 border-b bg-white flex items-center justify-between px-4">
          {active ? (
            <div className="min-w-0">
              <span className="block font-semibold text-slate-800 truncate">
                {active.name || active.wa_id}
              </span>
              <div className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                <span className="min-w-0 flex items-center gap-1 truncate">
                  <Phone size={12} />
                  {active.wa_id}
                </span>
                <button
                  type="button"
                  onClick={copyPhone}
                  className="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  title="Copy phone number"
                >
                  {copiedPhoneFor === active.id ? <Check size={12} /> : <Copy size={12} />}
                </button>
              </div>
            </div>
          ) : (
            <span className="font-semibold text-slate-800">Select a conversation</span>
          )}
          <div className="flex items-center gap-2">
            {active && (
              <button onClick={togglePause}
                className={`flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg ${
                  active.ai_paused
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'}`}>
                {active.ai_paused ? <BotOff size={16} /> : <Bot size={16} />}
                {active.ai_paused ? 'AI paused' : 'AI active'}
              </button>
            )}
            <button onClick={() => setShowSettings(true)} className="p-2 text-slate-500 hover:text-slate-800">
              <Settings size={18} />
            </button>
            <button onClick={logout} className="p-2 text-slate-500 hover:text-red-600">
              <LogOut size={18} />
            </button>
          </div>
        </div>
        {active ? (
          <>
            <ChatThread messages={messages} />
            <Composer conversationId={active.id} onSent={onSent} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            Pick a conversation to start
          </div>
        )}
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      {showTemplate && (
        <NewTemplateModal
          onClose={() => setShowTemplate(false)}
          onSent={(cid) => { refreshConversations(); setActiveId(cid) }}
        />
      )}
    </div>
  )
}
