import { useEffect, useState } from "react"
import { apiGetAgents, apiGetThread } from "~lib/api"
import type { Agent } from "~lib/types"
import { ROLE_GRADIENTS, ROLE_ICONS, WELCOME_MESSAGES } from "~lib/agent-constants"

export default function CompanionList({ 
  onSelect, 
  selectedId 
}: { 
  onSelect: (agent: Agent) => void
  selectedId?: string
}) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [previews, setPreviews] = useState<Record<string, string>>({})

  useEffect(() => {
    apiGetAgents()
      .then(async (res) => {
        const activeAgents = res.agents.filter((a) => a.is_active)
        setAgents(activeAgents)
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
    <div className="p-3 space-y-2 h-full overflow-y-auto">
      {agents.map((agent) => {
        const icon = ROLE_ICONS[agent.role] || "🤖"
        const gradient = ROLE_GRADIENTS[agent.role] || "from-gray-400 to-gray-500"
        const preview = previews[agent.id]
          || WELCOME_MESSAGES[agent.role]
          || agent.purpose
        const isSelected = selectedId === agent.id

        return (
          <button
            key={agent.id}
            onClick={() => onSelect(agent)}
            className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${
              isSelected 
                ? "bg-primary-50 border-primary-300 shadow-sm" 
                : "bg-white border-surface-200 hover:border-primary-300 hover:shadow-sm active:scale-[0.98]"
            }`}
          >
            <div className={`w-11 h-11 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-xl shadow-sm flex-shrink-0`}>
              {icon}
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-surface-800 truncate">{agent.name}</h3>
              <p className="text-xs text-surface-400 truncate">{preview}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
