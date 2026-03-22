import { useEffect, useRef, useState } from "react"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import JournalEditor from "~components/JournalEditor"
import ChatWindow from "~components/ChatWindow"
import CompanionList from "~components/CompanionList"
import type { Agent } from "~lib/types"
import { apiGetUnreadTotal } from "~lib/api"
import { useAuthStore } from "~store/authStore"

type Mode = "journal" | "chat"



// ---- Main SidePanel ----
function SidePanel() {
  const { user, loading, init } = useAuthStore()
  const [mode, setMode] = useState<Mode>(() => {
    const hash = window.location.hash.replace("#", "")
    return hash === "chat" ? "chat" : "journal"
  })
  const [chatAgent, setChatAgent] = useState<Agent | null>(null)
  const [unreadTotal, setUnreadTotal] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    init()
  }, [])

  useEffect(() => {
    if (mode !== "chat") {
      apiGetUnreadTotal()
        .then((res) => setUnreadTotal(res.unread_total))
        .catch(() => {})
    } else {
      setUnreadTotal(0)
    }
  }, [mode])

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-50">
        <div className="animate-pulse text-surface-400">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <AuthForm />
  }

  // Chat window view (full screen)
  if (mode === "chat" && chatAgent) {
    return <ChatWindow agent={chatAgent} onBack={() => setChatAgent(null)} onRead={() => {
      setRefreshKey((k) => k + 1)
      setUnreadTotal(0)
    }} />
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header with mode switcher */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📓</span>
            <div className="relative">
              <select
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value as Mode)
                  setChatAgent(null)
                }}
                className="text-sm font-bold text-primary-700 bg-transparent border-none
                  focus:outline-none focus:ring-0 cursor-pointer appearance-none
                  pr-5 bg-no-repeat bg-right"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236366f1' d='M3 5l3 3 3-3'/%3E%3C/svg%3E")`,
                  backgroundPosition: "right 0 center",
                }}
              >
                <option value="journal">Quick Entry</option>
                <option value="chat">AI Chat</option>
              </select>
              {mode !== "chat" && unreadTotal > 0 && (
                <span className="absolute -top-1 -right-2 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white animate-pulse">
                  {unreadTotal > 9 ? "9+" : unreadTotal}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => {
              chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html") })
            }}
            className="text-xs px-2.5 py-1 rounded-lg text-surface-500 hover:text-primary-600 hover:bg-primary-50 transition"
          >
            Full View →
          </button>
        </div>
      </div>

      {/* Content based on mode */}
      {mode === "journal" ? (
        <div className="p-4">
          <JournalEditor sourceSurface="sidepanel" compact />
        </div>
      ) : (
        <CompanionList onSelect={(agent) => setChatAgent(agent)} refreshKey={refreshKey} />
      )}
    </div>
  )
}

export default SidePanel
