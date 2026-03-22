import { useEffect, useState } from "react"
import { HashRouter, Route, Routes, useNavigate, useParams } from "react-router-dom"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import Calendar from "~components/Calendar"
import ChatThread from "~components/ChatThread"
import GoalsDashboard from "~components/GoalsDashboard"

import JournalCard from "~components/JournalCard"
import JournalEditor from "~components/JournalEditor"
import ChatWindow from "~components/ChatWindow"
import CompanionList from "~components/CompanionList"
import Layout from "~components/Layout"
import { apiCreateAgent, apiDeleteAccount, apiDeleteAgent, apiExportJournals, apiGetAgents, apiGetInsights, apiGetJournalsByDate, apiImportJournals, apiToggleAgent, apiUpdateAgent } from "~lib/api"
import type { InsightsData } from "~lib/api"
import type { Agent, Journal } from "~lib/types"
import { useAuthStore } from "~store/authStore"
import { useJournalStore } from "~store/journalStore"

// ---- Home Page ----
function HomePage() {
  const navigate = useNavigate()
  const { journals, total, loading, fetchJournals } = useJournalStore()

  useEffect(() => {
    fetchJournals(5)
  }, [])

  return (
    <Layout title="Dashboard">
      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <button
          onClick={() => navigate("/journal/new")}
          className="p-6 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/20 hover:shadow-primary-500/30 hover:scale-[1.02] transition-all text-left"
        >
          <span className="text-2xl mb-2 block">✏️</span>
          <h3 className="font-semibold text-lg">New Entry</h3>
          <p className="text-primary-100/80 text-sm mt-1">Start writing today's journal</p>
        </button>
        <button
          onClick={() => navigate("/chat")}
          className="p-6 rounded-2xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
        >
          <span className="text-2xl mb-2 block">💬</span>
          <h3 className="font-semibold text-lg text-surface-800">Chat</h3>
          <p className="text-surface-500 text-sm mt-1">Talk to AI companions</p>
        </button>
        <button
          onClick={() => navigate("/goals")}
          className="p-6 rounded-2xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
        >
          <span className="text-2xl mb-2 block">🎯</span>
          <h3 className="font-semibold text-lg text-surface-800">Goals</h3>
          <p className="text-surface-500 text-sm mt-1">Track your goals & tasks</p>
        </button>
        <button
          onClick={() => navigate("/insights")}
          className="p-6 rounded-2xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
        >
          <span className="text-2xl mb-2 block">✨</span>
          <h3 className="font-semibold text-lg text-surface-800">Insights</h3>
          <p className="text-surface-500 text-sm mt-1">AI summaries & themes</p>
        </button>
      </div>

      {/* Recent entries */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-surface-800">Recent Entries</h2>
          {total > 5 && (
            <button
              onClick={() => navigate("/history")}
              className="text-sm text-primary-600 hover:text-primary-500 transition"
            >
              View all →
            </button>
          )}
        </div>
        {loading && journals.length === 0 ? (
          <div className="text-center py-12 text-surface-400">Loading...</div>
        ) : journals.length === 0 ? (
          <div className="text-center py-12">
            <span className="text-4xl block mb-3">📝</span>
            <p className="text-surface-500">No entries yet. Start your first journal!</p>
            <button
              onClick={() => navigate("/journal/new")}
              className="mt-4 px-5 py-2.5 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium transition shadow-lg"
            >
              Write First Entry
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {journals.map((j) => (
              <JournalCard
                key={j.id}
                journal={j}
                onClick={() => navigate(`/journal/${j.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

// ---- New Journal Page ----
function NewJournalPage() {
  const navigate = useNavigate()

  return (
    <Layout title="New Journal Entry">
      <JournalEditor
        sourceSurface="fullpage"
        onSaved={(id) => navigate(`/journal/${id}`)}
      />
    </Layout>
  )
}

// ---- View Journal Page ----
function ViewJournalPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentJournal, loading, fetchJournal, updateJournal, deleteJournal, clearCurrent } = useJournalStore()
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const [editContent, setEditContent] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (id) fetchJournal(id)
    return () => clearCurrent()
  }, [id])

  // Auto-refresh journal while it's being processed (title, status)
  useEffect(() => {
    if (!id || !currentJournal) return
    if (currentJournal.status !== "submitted") return
    const interval = setInterval(() => fetchJournal(id), 3000)
    return () => clearInterval(interval)
  }, [id, currentJournal?.status])

  // Sync edit fields when journal data loads or changes (only when not editing)
  useEffect(() => {
    if (currentJournal && !isEditing) {
      setEditTitle(currentJournal.title || "")
      setEditContent(currentJournal.raw_text || "")
    }
  }, [currentJournal, isEditing])

  const handleDelete = async () => {
    if (!id || !confirm("Delete this journal entry?")) return
    await deleteJournal(id)
    navigate("/history")
  }

  const handleStartEdit = () => {
    setEditTitle(currentJournal?.title || "")
    setEditContent(currentJournal?.raw_text || "")
    setIsEditing(true)
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
  }

  const handleSave = async () => {
    if (!id) return
    setSaving(true)
    try {
      await updateJournal(id, {
        title: editTitle || undefined,
        content: editContent,
      })
      setIsEditing(false)
    } catch {
      // error handled by store
    } finally {
      setSaving(false)
    }
  }

  if (loading || !currentJournal) {
    return (
      <Layout>
        <div className="text-center py-12 text-surface-400">
          {loading ? "Loading..." : "Journal not found"}
        </div>
      </Layout>
    )
  }

  const date = new Date(currentJournal.created_at)

  return (
    <Layout>
      <div className="flex flex-col h-[calc(100vh-104px)] max-w-3xl mx-auto pb-2">
        {/* Top Scrollable Section */}
        <div className="flex-shrink overflow-y-auto mb-4 pr-1">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate(-1)}
              className="text-sm text-surface-500 hover:text-primary-600 transition mb-3 inline-flex items-center gap-1"
            >
              ← Back
            </button>
            <div className="flex items-start justify-between">
              <div className="flex-1 mr-4">
                {isEditing ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="Journal title..."
                    className="text-2xl font-bold text-surface-900 bg-transparent border-b-2 border-primary-300 focus:border-primary-500 focus:outline-none w-full pb-1"
                  />
                ) : (
                  <h1 className="text-2xl font-bold text-surface-900">
                    {currentJournal.title || "Untitled Entry"}
                  </h1>
                )}
                <p className="text-sm text-surface-400 mt-1">
                  {date.toLocaleDateString("en-US", {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })} at {date.toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {currentJournal.mood_label && (
                  <span className="text-2xl">{currentJournal.mood_label}</span>
                )}
                {isEditing ? (
                  <>
                    <button
                      onClick={handleCancelEdit}
                      className="text-sm px-3 py-1.5 rounded-lg text-surface-500 hover:text-surface-700 hover:bg-surface-100 transition"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="text-sm px-4 py-1.5 rounded-lg bg-primary-500 text-white hover:bg-primary-400 disabled:opacity-50 transition font-medium"
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={handleStartEdit}
                      className="text-sm px-3 py-1.5 rounded-lg text-primary-600 hover:text-primary-700 hover:bg-primary-50 transition"
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={handleDelete}
                      className="text-sm px-3 py-1.5 rounded-lg text-red-500 hover:text-red-700 hover:bg-red-50 transition"
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="prose prose-lg max-w-none">
            {isEditing ? (
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full p-6 rounded-2xl bg-white border border-primary-300 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none text-surface-700 leading-relaxed resize-y min-h-[200px]"
                rows={Math.max(10, editContent.split("\n").length + 2)}
              />
            ) : (
              <div className="p-6 rounded-2xl bg-white border border-surface-200 whitespace-pre-wrap break-words text-surface-700 leading-relaxed">
                {currentJournal.raw_text}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="mt-4 flex gap-4 text-xs text-surface-400">
            {currentJournal.word_count && (
              <span>{currentJournal.word_count} words</span>
            )}
            {currentJournal.source_surface && (
              <span>Written in {currentJournal.source_surface}</span>
            )}
            <span className="flex items-center gap-1">
              Status: {currentJournal.status}
              {(currentJournal.status === "processed" || currentJournal.status === "failed") && (
                <button
                  onClick={async () => {
                    try {
                      await updateJournal(currentJournal.id, { submit: true })
                    } catch {}
                  }}
                  className="hover:bg-surface-100 p-0.5 rounded transition text-surface-400 hover:text-surface-600 flex items-center justify-center"
                  title="Re-process Journal"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                    <path d="M3 3v5h5"/>
                  </svg>
                </button>
              )}
            </span>
          </div>
        </div>

        {/* Follow-up Chat */}
        {(currentJournal.status === "processed" || currentJournal.status === "submitted") && (
          <ChatThread 
            className="flex-1 min-h-[300px]"
            journalId={currentJournal.id} 
            defaultAgentRole="reflection_coach" 
            journalStatus={currentJournal.status} 
          />
        )}
      </div>
    </Layout>
  )
}

// ---- History Page ----
function HistoryPage() {
  const navigate = useNavigate()
  const [selectedDate, setSelectedDate] = useState<{ year: number; month: number; day: number } | null>(null)
  const [dateJournals, setDateJournals] = useState<Journal[]>([])
  const [dateLoading, setDateLoading] = useState(false)

  const handleDateSelect = async (year: number, month: number, day: number) => {
    setSelectedDate({ year, month, day })
    setDateLoading(true)
    try {
      const res = await apiGetJournalsByDate(year, month, day)
      setDateJournals(res.journals)
    } catch {
      setDateJournals([])
    } finally {
      setDateLoading(false)
    }
  }

  const formatSelectedDate = () => {
    if (!selectedDate) return ""
    const d = new Date(selectedDate.year, selectedDate.month - 1, selectedDate.day)
    return d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  return (
    <Layout title="Journal History">
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Calendar */}
        <div>
          <Calendar onDateSelect={handleDateSelect} selectedDate={selectedDate} />
        </div>

        {/* Journal entries for selected date */}
        <div>
          {!selectedDate ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <span className="text-5xl mb-4">📅</span>
              <h3 className="text-lg font-semibold text-surface-700 mb-2">Select a Date</h3>
              <p className="text-surface-400 text-sm max-w-xs">
                Click on a highlighted day in the calendar to view your journal entries for that date.
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-surface-800">
                  {formatSelectedDate()}
                </h2>
                <p className="text-sm text-surface-400 mt-0.5">
                  {dateJournals.length} {dateJournals.length === 1 ? "entry" : "entries"}
                </p>
              </div>

              {dateLoading ? (
                <div className="text-center py-12 text-surface-400 animate-pulse">Loading entries...</div>
              ) : dateJournals.length === 0 ? (
                <div className="text-center py-12">
                  <span className="text-3xl block mb-2">📝</span>
                  <p className="text-surface-500 text-sm">No entries for this date.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dateJournals.map((j) => (
                    <JournalCard
                      key={j.id}
                      journal={j}
                      onClick={() => navigate(`/journal/${j.id}`)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}

// ---- Agents Page ----
function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: "", purpose: "", tone: "", system_prompt: "" })
  const [saving, setSaving] = useState(false)

  const loadAgents = () => {
    setLoading(true)
    apiGetAgents()
      .then((res) => setAgents(res.agents))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadAgents() }, [])

  const handleCreate = async () => {
    if (!form.name.trim() || !form.purpose.trim() || !form.tone.trim()) return
    setSaving(true)
    try {
      await apiCreateAgent({
        name: form.name.trim(),
        purpose: form.purpose.trim(),
        tone: form.tone.trim(),
        system_prompt: form.system_prompt.trim() || undefined,
      })
      setForm({ name: "", purpose: "", tone: "", system_prompt: "" })
      setShowCreate(false)
      loadAgents()
    } catch { }
    setSaving(false)
  }

  const handleEdit = (agent: Agent) => {
    setEditingId(agent.id)
    setForm({
      name: agent.name,
      purpose: agent.purpose,
      tone: agent.tone,
      system_prompt: "",
    })
  }

  const handleUpdate = async () => {
    if (!editingId) return
    setSaving(true)
    try {
      await apiUpdateAgent(editingId, {
        name: form.name.trim() || undefined,
        purpose: form.purpose.trim() || undefined,
        tone: form.tone.trim() || undefined,
        system_prompt: form.system_prompt.trim() || undefined,
      })
      setEditingId(null)
      setForm({ name: "", purpose: "", tone: "", system_prompt: "" })
      loadAgents()
    } catch { }
    setSaving(false)
  }

  const handleDelete = async (agentId: string) => {
    if (!confirm("Delete this custom agent? This cannot be undone.")) return
    try {
      await apiDeleteAgent(agentId)
      loadAgents()
    } catch { }
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

  const renderForm = (isEdit: boolean) => (
    <div className="rounded-2xl bg-white border border-primary-200 shadow-lg p-6 mb-6">
      <h3 className="font-semibold text-lg text-surface-900 mb-4">
        {isEdit ? "Edit Agent" : "✨ Create Custom Agent"}
      </h3>
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-surface-600 mb-1">Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Fitness Buddy"
            className="w-full px-4 py-2.5 rounded-xl border border-surface-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-400 focus:outline-none text-surface-800"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-600 mb-1">Purpose</label>
          <textarea
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
            placeholder="What does this agent help with?"
            rows={2}
            className="w-full px-4 py-2.5 rounded-xl border border-surface-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-400 focus:outline-none text-surface-800 resize-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-600 mb-1">Tone</label>
          <input
            type="text"
            value={form.tone}
            onChange={(e) => setForm({ ...form, tone: e.target.value })}
            placeholder="e.g. motivating, direct, lighthearted"
            className="w-full px-4 py-2.5 rounded-xl border border-surface-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-400 focus:outline-none text-surface-800"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-surface-600 mb-1">
            System Prompt <span className="text-surface-400">(optional)</span>
          </label>
          <textarea
            value={form.system_prompt}
            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            placeholder="Custom instructions for the AI (advanced)"
            rows={3}
            className="w-full px-4 py-2.5 rounded-xl border border-surface-200 focus:border-primary-400 focus:ring-1 focus:ring-primary-400 focus:outline-none text-surface-800 resize-none"
          />
        </div>
        <div className="flex gap-2 pt-2">
          <button
            onClick={isEdit ? handleUpdate : handleCreate}
            disabled={saving || !form.name.trim() || !form.purpose.trim() || !form.tone.trim()}
            className="px-5 py-2.5 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium transition disabled:opacity-50 shadow-lg"
          >
            {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Agent"}
          </button>
          <button
            onClick={() => {
              isEdit ? setEditingId(null) : setShowCreate(false)
              setForm({ name: "", purpose: "", tone: "", system_prompt: "" })
            }}
            className="px-4 py-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
  const renderAgentCard = (agent: Agent) => {
    const icon = ROLE_ICONS[agent.role] || "🤖"
    const gradient = ROLE_COLORS[agent.role] || "from-sky-400 to-indigo-500"
    return (
      <div
        key={agent.id}
        className={`rounded-2xl bg-white border border-surface-200 overflow-hidden hover:shadow-md transition-all ${!agent.is_active ? "opacity-60 grayscale-[0.2]" : ""}`}
      >
        <div className={`h-2 bg-gradient-to-r ${gradient}`} />
        <div className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl">{icon}</span>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-surface-900">{agent.name}</h3>
              <span className={`text-xs ${agent.is_builtin ? "text-surface-400" : "text-primary-500 font-medium"}`}>
                {agent.is_builtin ? "Built-in" : "Custom"}
              </span>
            </div>
            {!agent.is_builtin && !editingId && (
              <div className="flex gap-1">
                <button
                  onClick={() => handleEdit(agent)}
                  className="p-1.5 rounded-lg text-surface-400 hover:text-primary-600 hover:bg-primary-50 transition"
                  title="Edit"
                >
                  ✏️
                </button>
                <button
                  onClick={() => handleDelete(agent.id)}
                  className="p-1.5 rounded-lg text-surface-400 hover:text-red-600 hover:bg-red-50 transition"
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
            )}
          </div>
          <p className="text-sm text-surface-600 leading-relaxed mb-2">
            {agent.purpose}
          </p>
          <p className="text-xs text-surface-400">
            Tone: <span className="text-surface-500">{agent.tone}</span>
          </p>
          {/* Toggle switch */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-surface-100">
            <span className="text-xs text-surface-500">
              {agent.is_active ? "Active" : "Inactive"}
            </span>
            <button
              onClick={async () => {
                try {
                  const updated = await apiToggleAgent(agent.id)
                  setAgents((prev) => prev.map((a) => a.id === agent.id ? { ...a, is_active: updated.is_active } : a))
                } catch {}
              }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                agent.is_active ? "bg-primary-500" : "bg-surface-300"
              }`}
              title={agent.is_active ? "Deactivate" : "Activate"}
            >
              <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform ${
                agent.is_active ? "translate-x-5" : "translate-x-0.5"
              }`} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  const activeAgents = agents.filter(a => a.is_active)
  const disabledAgents = agents.filter(a => !a.is_active)

  return (
    <Layout title="AI Agents">
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-6">
          <p className="text-surface-500">
            These AI companions each bring a unique perspective to your journal reflections.
          </p>
          {!showCreate && !editingId && (
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white font-medium hover:shadow-lg hover:shadow-primary-500/20 transition-all text-sm whitespace-nowrap ml-4"
            >
              + New Agent
            </button>
          )}
        </div>

        {showCreate && renderForm(false)}
        {editingId && renderForm(true)}

        {loading ? (
          <div className="text-center py-12 text-surface-400 animate-pulse">Loading agents...</div>
        ) : (
          <div className="space-y-8">
            {activeAgents.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-surface-900 mb-4">Active</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {activeAgents.map(renderAgentCard)}
                </div>
              </div>
            )}
            
            {disabledAgents.length > 0 && (
              <div className="pt-2">
                <h2 className="text-lg font-semibold text-surface-500 mb-4">Disabled</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {disabledAgents.map(renderAgentCard)}
                </div>
              </div>
            )}

            {agents.length === 0 && (
              <div className="text-center py-12 text-surface-400">No agents found.</div>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}

// ---- Insights Page ----
function InsightsPage() {
  const [period, setPeriod] = useState<"weekly" | "monthly">("weekly")
  const [data, setData] = useState<InsightsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setData(null)
    apiGetInsights(period)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [period])

  return (
    <Layout title="Insights">
      <div className="max-w-3xl">
        {/* Period Toggle */}
        <div className="flex gap-2 mb-6">
          {(["weekly", "monthly"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-5 py-2.5 rounded-xl font-medium text-sm transition-all ${
                period === p
                  ? "bg-primary-500 text-white shadow-lg shadow-primary-500/20"
                  : "bg-white border border-surface-200 text-surface-600 hover:border-primary-300"
              }`}
            >
              {p === "weekly" ? "📅 This Week" : "📆 This Month"}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="animate-pulse text-surface-400">Analyzing your journals...</div>
          </div>
        ) : !data ? (
          <div className="text-center py-16 text-surface-400">Something went wrong.</div>
        ) : (
          <div className="space-y-4">
            {/* Summary */}
            <div className="rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 text-white p-6 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg">
                  {period === "weekly" ? "Week" : "Month"} in Review
                </h3>
                <span className="text-primary-100 text-sm">
                  {data.journal_count} {data.journal_count === 1 ? "entry" : "entries"}
                </span>
              </div>
              <p className="text-primary-50 leading-relaxed">{data.summary}</p>
            </div>

            {/* Themes */}
            {data.themes.length > 0 && (
              <div className="rounded-2xl bg-white border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-3">🏷️ Key Themes</h3>
                <div className="flex flex-wrap gap-2">
                  {data.themes.map((t, i) => (
                    <span key={i} className="px-3 py-1.5 rounded-full bg-primary-50 text-primary-700 text-sm font-medium">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Mood Trend */}
            <div className="rounded-2xl bg-white border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-2">💭 Mood Trend</h3>
              <p className="text-surface-600 text-sm leading-relaxed">{data.mood_trend}</p>
            </div>

            {/* Accomplishments */}
            {data.accomplishments.length > 0 && (
              <div className="rounded-2xl bg-white border border-surface-200 p-6">
                <h3 className="font-semibold text-surface-900 mb-3">🏆 Accomplishments</h3>
                <ul className="space-y-2">
                  {data.accomplishments.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-surface-600">
                      <span className="text-emerald-500 mt-0.5">✓</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Reflection Prompts */}
            {data.reflection_prompts.length > 0 && (
              <div className="rounded-2xl bg-gradient-to-br from-violet-50 to-purple-50 border border-violet-200 p-6">
                <h3 className="font-semibold text-violet-900 mb-3">🔮 Reflect On</h3>
                <ul className="space-y-3">
                  {data.reflection_prompts.map((q, i) => (
                    <li key={i} className="text-sm text-violet-700 italic leading-relaxed">
                      "{q}"
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}

// ---- Goals Page ----
function GoalsPage() {
  return (
    <Layout title="Goals & Tasks">
      <GoalsDashboard />
    </Layout>
  )
}

// ---- Settings Page ----
function SettingsPage() {
  const { user, logout: authLogout } = useAuthStore()
  const navigate = useNavigate()
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ imported: number; skipped: number; total: number } | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")
  const [deleting, setDeleting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      await apiExportJournals()
    } catch {
      alert("Export failed. Please try again.")
    }
    setExporting(false)
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "DELETE") return
    setDeleting(true)
    try {
      await apiDeleteAccount()
      await authLogout()
      navigate("/")
    } catch {
      alert("Account deletion failed. Please try again.")
      setDeleting(false)
    }
  }

  return (
    <Layout title="Settings">
      <div className="max-w-2xl space-y-6">
        {/* Profile */}
        <div className="rounded-2xl bg-white border border-surface-200 p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-4">👤 Profile</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-surface-100">
              <span className="text-sm text-surface-500">Name</span>
              <span className="text-sm font-medium text-surface-800">{user?.name || "—"}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-surface-100">
              <span className="text-sm text-surface-500">Email</span>
              <span className="text-sm font-medium text-surface-800">{user?.email || "—"}</span>
            </div>
          </div>
        </div>

        {/* Export */}
        <div className="rounded-2xl bg-white border border-surface-200 p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-2">📦 Export Data</h3>
          <p className="text-sm text-surface-500 mb-4">
            Download all your journal entries as a JSON file. This includes titles, content, mood labels, and metadata.
          </p>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-5 py-2.5 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium transition disabled:opacity-50 shadow-lg"
          >
            {exporting ? "Exporting..." : "Download All Journals"}
          </button>
        </div>

        {/* Import */}
        <div className="rounded-2xl bg-white border border-surface-200 p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-2">📥 Import Data</h3>
          <p className="text-sm text-surface-500 mb-4">
            Upload a previously exported JSON file. Duplicate entries will be skipped. Imported journals will be processed for memory extraction and goal/task analysis.
          </p>
          <div className="flex items-center gap-3">
            <label
              className={`px-5 py-2.5 rounded-xl font-medium transition shadow-lg cursor-pointer ${
                importing
                  ? "bg-surface-300 text-surface-500"
                  : "bg-emerald-500 hover:bg-emerald-400 text-white"
              }`}
            >
              {importing ? "Importing..." : "Choose File & Import"}
              <input
                type="file"
                accept=".json"
                className="hidden"
                disabled={importing}
                onChange={async (e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  setImporting(true)
                  setImportResult(null)
                  try {
                    const text = await file.text()
                    const data = JSON.parse(text)
                    const result = await apiImportJournals(data)
                    setImportResult(result)
                  } catch {
                    alert("Import failed. Make sure the file is a valid MemoryJournal export.")
                  }
                  setImporting(false)
                  e.target.value = ""
                }}
              />
            </label>
          </div>
          {importResult && (
            <div className="mt-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800">
              ✅ Imported <strong>{importResult.imported}</strong> journal{importResult.imported !== 1 ? "s" : ""}.
              {importResult.skipped > 0 && (
                <> Skipped <strong>{importResult.skipped}</strong> duplicate{importResult.skipped !== 1 ? "s" : ""}.</>)}
              {importResult.imported > 0 && (
                <> Processing will run in the background.</>)}
            </div>
          )}
        </div>

        {/* Logout */}
        <div className="rounded-2xl bg-white border border-surface-200 p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-2">🔒 Session</h3>
          <button
            onClick={async () => { await authLogout(); navigate("/") }}
            className="px-5 py-2.5 rounded-xl bg-surface-100 hover:bg-surface-200 text-surface-700 font-medium transition"
          >
            Log Out
          </button>
        </div>

        {/* Danger Zone */}
        <div className="rounded-2xl bg-white border-2 border-red-200 p-6">
          <h3 className="text-lg font-semibold text-red-600 mb-2">⚠️ Danger Zone</h3>
          <p className="text-sm text-surface-600 mb-4">
            Permanently delete your account and all associated data including journals, goals, tasks, and agent conversations. <strong>This action cannot be undone.</strong>
          </p>
          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-5 py-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 font-medium transition border border-red-200"
            >
              Delete My Account
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-red-600 font-medium">
                Type <code className="bg-red-50 px-1.5 py-0.5 rounded">DELETE</code> to confirm:
              </p>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="Type DELETE"
                className="w-full px-4 py-2.5 rounded-xl border border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500 focus:outline-none text-surface-800"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleteConfirmText !== "DELETE" || deleting}
                  className="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-medium transition disabled:opacity-50"
                >
                  {deleting ? "Deleting..." : "Permanently Delete Account"}
                </button>
                <button
                  onClick={() => { setShowDeleteConfirm(false); setDeleteConfirmText("") }}
                  className="px-4 py-2.5 rounded-xl text-surface-500 hover:text-surface-700 hover:bg-surface-100 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

// ---- Root App ----
function TabsApp() {
  const { user, loading, init } = useAuthStore()

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

  // ---- Chat Page Component ----
  const ChatPage = () => {
    const [chatAgent, setChatAgent] = useState<Agent | null>(null)

    return (
      <Layout title="AI Chat">
        <div className="flex h-[80vh] bg-surface-50 rounded-2xl border border-surface-200 overflow-hidden shadow-sm mt-4">
          {/* Sidebar */}
          <div className={`w-full md:w-80 border-r border-surface-200 bg-white ${chatAgent ? "hidden md:flex md:flex-col" : "flex flex-col"}`}>
            <div className="p-4 border-b border-surface-100 flex-shrink-0">
              <h2 className="font-semibold text-lg text-surface-800">Companions</h2>
              <p className="text-sm text-surface-500">Select an AI to chat with</p>
            </div>
            <div className="flex-1 min-h-0 bg-surface-50/50">
              <CompanionList onSelect={setChatAgent} selectedId={chatAgent?.id} />
            </div>
          </div>
          
          {/* Main Chat Area */}
          <div className={`flex-1 bg-white flex flex-col min-w-0 ${chatAgent ? "block" : "hidden md:flex md:items-center md:justify-center"}`}>
            {chatAgent ? (
              <ChatWindow 
                agent={chatAgent} 
                onBack={() => setChatAgent(null)} 
                isFullScreen={true}
              />
            ) : (
              <div className="text-center text-surface-400">
                <span className="text-6xl mb-4 block opacity-20">💬</span>
                <p className="text-lg font-medium text-surface-500">Select a companion to start chatting</p>
              </div>
            )}
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/journal/new" element={<NewJournalPage />} />
        <Route path="/journal/:id" element={<ViewJournalPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/goals" element={<GoalsPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </HashRouter>
  )
}

export default TabsApp
