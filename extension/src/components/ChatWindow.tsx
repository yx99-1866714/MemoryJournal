import { useEffect, useRef, useState } from "react"
import { apiAgentRespond, apiClearThread, apiGetThread, apiMarkThreadRead } from "~lib/api"
import type { Agent, AgentMessage } from "~lib/types"
import { ROLE_GRADIENTS, ROLE_ICONS, WELCOME_MESSAGES } from "~lib/agent-constants"

export default function ChatWindow({
  agent,
  onBack,
  onRead,
  isFullScreen = false
}: {
  agent: Agent
  onBack?: () => void
  onRead?: () => void
  isFullScreen?: boolean
}) {
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [loadingThread, setLoadingThread] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
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
      .finally(() => {
        setLoadingThread(false)
        // Mark thread as read when opening
        apiMarkThreadRead(agent.id)
          .then(() => {
            if (onRead) onRead()
            try { chrome.runtime.sendMessage({ type: "thread-read" }) } catch {}
          })
          .catch(() => {})
      })
  }, [agent.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [input])

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
    <div className="flex flex-col h-full bg-surface-50 relative">
      {/* Chat header */}
      <div className="sticky top-0 z-40 bg-white/80 backdrop-blur-lg border-b border-surface-200">
        <div className="flex items-center gap-3 px-4 py-3">
          {onBack && (
            <button
              onClick={onBack}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface-100 text-surface-500 transition lg:hidden"
            >
              ←
            </button>
          )}
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
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {loadingThread ? (
          <div className="text-center py-12 animate-pulse text-surface-400 text-sm">
            Loading conversation...
          </div>
        ) : messages.length === 0 ? (
          <>
            {/* Welcome message */}
            <div className="flex justify-start">
              <span className="text-lg mr-2 mt-1 flex-shrink-0">{icon}</span>
              <div className="max-w-[85%] sm:max-w-[75%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap bg-white text-surface-700 rounded-2xl rounded-bl-md border border-surface-200 shadow-sm">
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
                <span className="text-lg mr-2 mt-1 flex-shrink-0">{icon}</span>
              )}
              <div
                className={`
                  max-w-[85%] sm:max-w-[75%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
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
            <span className="text-lg mr-2 mt-1">{icon}</span>
            <div className="bg-white text-surface-400 px-5 py-3 rounded-2xl rounded-bl-md border border-surface-200 shadow-sm">
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
      <div className="sticky bottom-0 p-3 bg-white/80 backdrop-blur-lg border-t border-surface-200">
        <div className="max-w-4xl mx-auto flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${agent.name}...`}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-surface-200 px-4 py-3 text-sm
              focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400
              placeholder:text-surface-400 transition shadow-sm max-h-[60vh] overflow-y-auto"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-4 py-3 rounded-xl bg-primary-500 text-white font-medium
              hover:bg-primary-400 disabled:opacity-40 disabled:cursor-not-allowed
              transition-all shadow-sm flex items-center justify-center min-w-[3rem]"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}
