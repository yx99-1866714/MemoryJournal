import { useEffect, useState } from "react"
import { HashRouter, Route, Routes, useNavigate, useParams } from "react-router-dom"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import Calendar from "~components/Calendar"
import ChatThread from "~components/ChatThread"
import GoalsDashboard from "~components/GoalsDashboard"

import JournalCard from "~components/JournalCard"
import JournalEditor from "~components/JournalEditor"
import Layout from "~components/Layout"
import { apiGetAgents, apiGetJournalsByDate } from "~lib/api"
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <button
          onClick={() => navigate("/journal/new")}
          className="p-6 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/20 hover:shadow-primary-500/30 hover:scale-[1.02] transition-all text-left"
        >
          <span className="text-2xl mb-2 block">✏️</span>
          <h3 className="font-semibold text-lg">New Entry</h3>
          <p className="text-primary-100/80 text-sm mt-1">Start writing today's journal</p>
        </button>
        <button
          onClick={() => navigate("/history")}
          className="p-6 rounded-2xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
        >
          <span className="text-2xl mb-2 block">📚</span>
          <h3 className="font-semibold text-lg text-surface-800">History</h3>
          <p className="text-surface-500 text-sm mt-1">{total} journal entries</p>
        </button>
        <button
          onClick={() => navigate("/goals")}
          className="p-6 rounded-2xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
        >
          <span className="text-2xl mb-2 block">🎯</span>
          <h3 className="font-semibold text-lg text-surface-800">Goals</h3>
          <p className="text-surface-500 text-sm mt-1">Track your goals & tasks</p>
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
      <div className="max-w-3xl mx-auto">
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
            <div className="p-6 rounded-2xl bg-white border border-surface-200 whitespace-pre-wrap text-surface-700 leading-relaxed">
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
          <span>Status: {currentJournal.status}</span>
        </div>

        {/* AI Feedback */}


        {/* Follow-up Chat */}
        {(currentJournal.status === "processed" || currentJournal.status === "submitted") && (
          <ChatThread journalId={currentJournal.id} defaultAgentRole="reflection_coach" journalStatus={currentJournal.status} />
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

  useEffect(() => {
    apiGetAgents()
      .then((res) => setAgents(res.agents))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

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

  return (
    <Layout title="AI Agents">
      <div className="max-w-3xl">
        <p className="text-surface-500 mb-6">
          These AI companions each bring a unique perspective to your journal reflections.
        </p>

        {loading ? (
          <div className="text-center py-12 text-surface-400 animate-pulse">Loading agents...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {agents.map((agent) => {
              const icon = ROLE_ICONS[agent.role] || "🤖"
              const gradient = ROLE_COLORS[agent.role] || "from-gray-400 to-gray-500"
              return (
                <div
                  key={agent.id}
                  className="rounded-2xl bg-white border border-surface-200 overflow-hidden hover:shadow-md transition-all"
                >
                  <div className={`h-2 bg-gradient-to-r ${gradient}`} />
                  <div className="p-5">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-3xl">{icon}</span>
                      <div>
                        <h3 className="font-semibold text-surface-900">{agent.name}</h3>
                        <span className="text-xs text-surface-400">
                          {agent.is_builtin ? "Built-in" : "Custom"}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-surface-600 leading-relaxed mb-2">
                      {agent.purpose}
                    </p>
                    <p className="text-xs text-surface-400">
                      Tone: <span className="text-surface-500">{agent.tone}</span>
                    </p>
                  </div>
                </div>
              )
            })}
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

// ---- Settings Page (Placeholder) ----
function SettingsPage() {
  return (
    <Layout title="Settings">
      <div className="max-w-2xl">
        <div className="p-6 rounded-2xl bg-white border border-surface-200">
          <p className="text-surface-500">
            Settings, privacy controls, and export/delete features will be available in Phase 5.
          </p>
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

  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/journal/new" element={<NewJournalPage />} />
        <Route path="/journal/:id" element={<ViewJournalPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/goals" element={<GoalsPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </HashRouter>
  )
}

export default TabsApp
