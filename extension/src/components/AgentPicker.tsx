import { useEffect, useState } from "react"
import { apiGetAgents } from "~lib/api"
import type { Agent } from "~lib/types"

interface AgentPickerProps {
  selectedAgentId: string | null
  onSelect: (agent: Agent) => void
}

const ROLE_ICONS: Record<string, string> = {
  reflection_coach: "🪞",
  goal_secretary: "📋",
  supportive_friend: "💛",
  inner_caregiver: "🤗",
}

const ROLE_COLORS: Record<string, string> = {
  reflection_coach: "from-violet-500 to-purple-600",
  goal_secretary: "from-emerald-500 to-teal-600",
  supportive_friend: "from-amber-400 to-orange-500",
  inner_caregiver: "from-rose-400 to-pink-500",
}

export default function AgentPicker({ selectedAgentId, onSelect }: AgentPickerProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGetAgents()
      .then((res) => {
        setAgents(res.agents)
        // Auto-select first agent if none selected
        if (!selectedAgentId && res.agents.length > 0) {
          onSelect(res.agents[0])
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex gap-2 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 w-24 rounded-xl bg-surface-100" />
        ))}
      </div>
    )
  }

  if (agents.length === 0) return null

  return (
    <div className="mb-4">
      <label className="block text-xs font-medium text-surface-500 mb-2 uppercase tracking-wider">
        Choose your AI companion
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {agents.map((agent) => {
          const isSelected = selectedAgentId === agent.id
          const icon = ROLE_ICONS[agent.role] || "🤖"
          const gradient = ROLE_COLORS[agent.role] || "from-gray-400 to-gray-500"

          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => onSelect(agent)}
              className={`
                relative p-3 rounded-xl text-left transition-all duration-200
                ${isSelected
                  ? `bg-gradient-to-br ${gradient} text-white shadow-lg scale-[1.02]`
                  : "bg-white border border-surface-200 hover:border-surface-300 hover:shadow-sm"
                }
              `}
            >
              <span className="text-lg block mb-0.5">{icon}</span>
              <span className={`text-xs font-semibold block leading-tight ${isSelected ? "text-white" : "text-surface-700"}`}>
                {agent.name}
              </span>
              {isSelected && (
                <span className="absolute top-1.5 right-1.5 text-white/80 text-[10px]">✓</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
