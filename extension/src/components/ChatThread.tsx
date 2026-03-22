import { useEffect, useRef, useState } from "react"
import { apiAgentRespond, apiGetAgents, apiGetThread } from "~lib/api"
import type { Agent, AgentMessage } from "~lib/types"

interface ChatThreadProps {
  journalId: string
  /** The agent that generated feedback, used as default */
  defaultAgentRole?: string
  /** Current journal processing status */
  journalStatus?: string
}

const ROLE_ICONS: Record<string, string> = {
  reflection_coach: "🪞",
  goal_secretary: "📋",
  supportive_friend: "💛",
  inner_caregiver: "🤗",
}

export default function ChatThread({ journalId, defaultAgentRole, journalStatus }: ChatThreadProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isProcessing = journalStatus && journalStatus !== "processed" && journalStatus !== "failed"

  // Load agents
  useEffect(() => {
    apiGetAgents()
      .then((res) => {
        setAgents(res.agents)
        const match = defaultAgentRole
          ? res.agents.find((a) => a.role === defaultAgentRole)
          : null
        setSelectedAgent(match || res.agents[0] || null)
      })
      .catch(() => {})
  }, [defaultAgentRole])

  // Load existing thread when agent changes
  useEffect(() => {
    if (!selectedAgent) return
    apiGetThread(selectedAgent.id, journalId)
      .then((thread) => {
        if (thread && thread.messages) {
          setMessages(thread.messages)
        } else {
          setMessages([])
        }
      })
      .catch(() => setMessages([]))
  }, [selectedAgent, journalId])

  // Auto-poll for messages while processing
  useEffect(() => {
    if (!isProcessing || !selectedAgent) return
    const interval = setInterval(() => {
      apiGetThread(selectedAgent.id, journalId)
        .then((thread) => {
          if (thread && thread.messages && thread.messages.length > 0) {
            setMessages(thread.messages)
          }
        })
        .catch(() => {})
    }, 3000)
    return () => clearInterval(interval)
  }, [isProcessing, selectedAgent, journalId])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || !selectedAgent || sending) return
    const text = input.trim()
    setInput("")
    setSending(true)

    // Optimistic user message
    const tempUserMsg: AgentMessage = {
      id: `temp-${Date.now()}`,
      thread_id: "",
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])

    try {
      const reply = await apiAgentRespond(selectedAgent.id, {
        message: text,
        journal_id: journalId,
        tz_offset_minutes: new Date().getTimezoneOffset(),
      })
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, reply])
    } catch (err) {
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
      setInput(text) // restore input
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

  if (agents.length === 0) return null

  return (
    <div className="mt-6 rounded-xl bg-white border border-surface-200 overflow-hidden">
      {/* Agent selector */}
      <div className="flex gap-1 px-3 py-2 border-b border-surface-100 bg-surface-50/50 overflow-x-auto">
        {agents.map((agent) => {
          const isSelected = selectedAgent?.id === agent.id
          const icon = ROLE_ICONS[agent.role] || "🤖"
          return (
            <button
              key={agent.id}
              onClick={() => setSelectedAgent(agent)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all
                ${isSelected
                  ? "bg-primary-500 text-white shadow-sm"
                  : "bg-white text-surface-600 hover:bg-surface-100 border border-surface-200"
                }
              `}
            >
              <span>{icon}</span>
              {agent.name}
            </button>
          )
        })}
      </div>

      {/* Messages */}
      <div className="max-h-80 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && isProcessing && (
          <div className="text-center py-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-50 text-primary-600 text-sm animate-pulse">
              <span>✨</span>
              Your companions are reading your journal...
            </div>
          </div>
        )}
        {messages.length === 0 && !isProcessing && (
          <div className="text-center py-8">
            <span className="text-3xl block mb-2">{ROLE_ICONS[selectedAgent?.role || ""] || "💬"}</span>
            <p className="text-sm text-surface-400">
              Send a message to {selectedAgent?.name || "the agent"}
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`
                max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
                ${msg.role === "user"
                  ? "bg-primary-500 text-white rounded-br-md"
                  : "bg-surface-100 text-surface-700 rounded-bl-md"
                }
              `}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-surface-100 text-surface-400 px-4 py-2.5 rounded-2xl rounded-bl-md text-sm">
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
      <div className="px-3 py-2.5 border-t border-surface-100 bg-surface-50/50">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask ${selectedAgent?.name || "the agent"} a question...`}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-surface-200 px-3.5 py-2 text-sm
              focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400
              placeholder:text-surface-400 transition"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-4 py-2 rounded-xl bg-primary-500 text-white text-sm font-medium
              hover:bg-primary-400 disabled:opacity-40 disabled:cursor-not-allowed
              transition-all shadow-sm"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
