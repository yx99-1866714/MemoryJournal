import { useEffect, useRef, useState } from "react"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import JournalEditor from "~components/JournalEditor"
import { apiAgentRespond, apiClearThread, apiGetAgents, apiGetThread } from "~lib/api"
import type { Agent, AgentMessage } from "~lib/types"
import { useAuthStore } from "~store/authStore"

type Mode = "journal" | "chat"

const ROLE_ICONS: Record<string, string> = {
  reflection_coach: "🪞",
  goal_secretary: "📋",
  supportive_friend: "💛",
  inner_caregiver: "🤗",
}

const ROLE_GRADIENTS: Record<string, string> = {
  reflection_coach: "from-violet-500 to-purple-600",
  goal_secretary: "from-emerald-500 to-teal-600",
  supportive_friend: "from-amber-400 to-orange-500",
  inner_caregiver: "from-rose-400 to-pink-500",
}

const WELCOME_MESSAGES: Record<string, string> = {
  reflection_coach:
    "Hey there \u{1F44B} I'm your Reflection Coach. I'm here to help you notice patterns and make sense of your experiences. What's on your mind today?",
  goal_secretary:
    "Hi! \u{1F4CB} I'm your Goal Secretary. I help you stay organized and follow through on what matters to you. What goals are you working towards?",
  supportive_friend:
    "Hey! \u{1F49B} I'm so glad you're here. I'm your Supportive Friend \u2014 think of me as someone who's always in your corner. How are you feeling today?",
  inner_caregiver:
    "Hello, dear one \u{1F338} I'm your Inner Caregiver. I'm here to remind you to be gentle with yourself. How are you taking care of yourself today?",
}

// ---- Chat Window Component ----
function ChatWindow({
  agent,
  onBack,
}: {
  agent: Agent
  onBack: () => void
}) {
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [loadingThread, setLoadingThread] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const icon = ROLE_ICONS[agent.role] || "🤖"
  const gradient = ROLE_GRADIENTS[agent.role] || "from-gray-400 to-gray-500"

  // Load existing thread (no journal context — free chat)
  useEffect(() => {
    setLoadingThread(true)
    apiGetThread(agent.id)
      .then((thread) => {
        if (thread?.messages) setMessages(thread.messages)
        else setMessages([])
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingThread(false))
  }, [agent.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const text = input.trim()
    setInput("")
    setSending(true)

    const tempMsg: AgentMessage = {
      id: `temp-${Date.now()}`,
      thread_id: "",
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempMsg])

    try {
      const reply = await apiAgentRespond(agent.id, { message: text })
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempMsg.id),
        tempMsg,
        reply,
      ])
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== tempMsg.id))
      setInput(text)
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-surface-50">
      {/* Chat header */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200">
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            onClick={onBack}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface-100 text-surface-500 transition"
          >
            ←
          </button>
          <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-base shadow-sm`}>
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-surface-800 truncate">{agent.name}</h2>
            <p className="text-[11px] text-surface-400 truncate">{agent.tone}</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={async () => {
                if (!confirm("Clear all chat history with this companion?")) return
                try {
                  await apiClearThread(agent.id)
                  setMessages([])
                } catch {}
              }}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 text-surface-400 hover:text-red-500 transition text-sm"
              title="Clear chat history"
            >
              🗑
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3">
        {loadingThread ? (
          <div className="text-center py-12 animate-pulse text-surface-400 text-sm">
            Loading conversation...
          </div>
        ) : messages.length === 0 ? (
          <>
            {/* Welcome message */}
            <div className="flex justify-start">
              <span className="text-sm mr-2 mt-1 flex-shrink-0">{icon}</span>
              <div className="max-w-[80%] px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap bg-white text-surface-700 rounded-2xl rounded-bl-md border border-surface-200 shadow-sm">
                {WELCOME_MESSAGES[agent.role] || `Hi! I'm your ${agent.name}. How can I help you today?`}
              </div>
            </div>
          </>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role !== "user" && (
                <span className="text-sm mr-2 mt-1 flex-shrink-0">{icon}</span>
              )}
              <div
                className={`
                  max-w-[80%] px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap
                  ${msg.role === "user"
                    ? "bg-primary-500 text-white rounded-2xl rounded-br-md shadow-sm"
                    : "bg-white text-surface-700 rounded-2xl rounded-bl-md border border-surface-200 shadow-sm"
                  }
                `}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        {sending && (
          <div className="flex justify-start">
            <span className="text-sm mr-2 mt-1">{icon}</span>
            <div className="bg-white text-surface-400 px-4 py-2.5 rounded-2xl rounded-bl-md border border-surface-200 text-sm shadow-sm">
              <span className="inline-flex gap-1">
                <span className="animate-bounce" style={{ animationDelay: "0ms" }}>·</span>
                <span className="animate-bounce" style={{ animationDelay: "150ms" }}>·</span>
                <span className="animate-bounce" style={{ animationDelay: "300ms" }}>·</span>
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="sticky bottom-0 px-3 py-2.5 bg-white/80 backdrop-blur-lg border-t border-surface-200">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${agent.name}...`}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-surface-200 px-3.5 py-2.5 text-sm
              focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400
              placeholder:text-surface-400 transition"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-3.5 py-2.5 rounded-xl bg-primary-500 text-white text-sm font-medium
              hover:bg-primary-400 disabled:opacity-40 disabled:cursor-not-allowed
              transition-all shadow-sm"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Companion List Component ----
function CompanionList({ onSelect }: { onSelect: (agent: Agent) => void }) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [previews, setPreviews] = useState<Record<string, string>>({})

  useEffect(() => {
    apiGetAgents()
      .then(async (res) => {
        setAgents(res.agents)
        // Fetch last message for each agent's thread
        const previewMap: Record<string, string> = {}
        await Promise.all(
          res.agents.map(async (agent) => {
            try {
              const thread = await apiGetThread(agent.id)
              if (thread?.messages?.length) {
                const last = thread.messages[thread.messages.length - 1]
                const prefix = last.role === "user" ? "You: " : ""
                previewMap[agent.id] = prefix + last.content
              }
            } catch {}
          })
        )
        setPreviews(previewMap)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-4 space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-surface-100 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="p-3 space-y-2">
      {agents.map((agent) => {
        const icon = ROLE_ICONS[agent.role] || "🤖"
        const gradient = ROLE_GRADIENTS[agent.role] || "from-gray-400 to-gray-500"
        const preview = previews[agent.id]
          || WELCOME_MESSAGES[agent.role]
          || agent.purpose
        return (
          <button
            key={agent.id}
            onClick={() => onSelect(agent)}
            className="w-full flex items-center gap-3 p-3 rounded-xl bg-white border border-surface-200
              hover:border-primary-300 hover:shadow-sm active:scale-[0.98] transition-all text-left"
          >
            <div className={`w-11 h-11 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-xl shadow-sm flex-shrink-0`}>
              {icon}
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-surface-800 truncate">{agent.name}</h3>
              <p className="text-xs text-surface-400 truncate">{preview}</p>
            </div>
            <span className="text-surface-300 text-sm flex-shrink-0">›</span>
          </button>
        )
      })}
    </div>
  )
}

// ---- Main SidePanel ----
function SidePanel() {
  const { user, loading, init } = useAuthStore()
  const [mode, setMode] = useState<Mode>(() => {
    const hash = window.location.hash.replace("#", "")
    return hash === "chat" ? "chat" : "journal"
  })
  const [chatAgent, setChatAgent] = useState<Agent | null>(null)

  useEffect(() => {
    init()
  }, [])

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
    return <ChatWindow agent={chatAgent} onBack={() => setChatAgent(null)} />
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header with mode switcher */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📓</span>
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
        <CompanionList onSelect={(agent) => setChatAgent(agent)} />
      )}
    </div>
  )
}

export default SidePanel
