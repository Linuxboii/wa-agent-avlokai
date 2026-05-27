import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { api } from './api'

export default function SettingsPanel({ onClose }) {
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getSettings().then((s) => {
      setPrompt(s.system_prompt || '')
      setModel(s.openai_model || 'gpt-4o-mini')
    })
  }, [])

  const save = async () => {
    await api.saveSettings(prompt, model)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="absolute inset-0 bg-black/30 flex justify-end z-10">
      <div className="w-96 bg-white h-full p-5 shadow-xl flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="font-semibold text-slate-800">AI Settings</h2>
          <button onClick={onClose}><X size={20} className="text-slate-500" /></button>
        </div>
        <label className="text-xs text-slate-500 mb-1">OpenAI model</label>
        <input className="border rounded-lg px-3 py-2 text-sm mb-4"
               value={model} onChange={(e) => setModel(e.target.value)} />
        <label className="text-xs text-slate-500 mb-1">System prompt</label>
        <textarea className="border rounded-lg px-3 py-2 text-sm flex-1 resize-none"
                  value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <button onClick={save}
                className="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg py-2 text-sm font-medium">
          {saved ? 'Saved ✓' : 'Save'}
        </button>
      </div>
    </div>
  )
}
