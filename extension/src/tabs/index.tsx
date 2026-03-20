import { useEffect, useState } from "react"
import { HashRouter, Route, Routes, useNavigate, useParams } from "react-router-dom"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import Calendar from "~components/Calendar"
import JournalCard from "~components/JournalCard"
import JournalEditor from "~components/JournalEditor"
import Layout from "~components/Layout"
import { apiGetJournalsByDate } from "~lib/api"
import type { Journal } from "~lib/types"
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
        <div className="p-6 rounded-2xl bg-white border border-surface-200 text-left opacity-60">
          <span className="text-2xl mb-2 block">🎯</span>
          <h3 className="font-semibold text-lg text-surface-800">Goals</h3>
          <p className="text-surface-400 text-sm mt-1">Coming in Phase 4</p>
        </div>
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
  const { currentJournal, loading, fetchJournal, deleteJournal, clearCurrent } = useJournalStore()

  useEffect(() => {
    if (id) fetchJournal(id)
    return () => clearCurrent()
  }, [id])

  const handleDelete = async () => {
    if (!id || !confirm("Delete this journal entry?")) return
    await deleteJournal(id)
    navigate("/history")
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
            <div>
              <h1 className="text-2xl font-bold text-surface-900">
                {currentJournal.title || "Untitled Entry"}
              </h1>
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
              <button
                onClick={handleDelete}
                className="text-sm px-3 py-1.5 rounded-lg text-red-500 hover:text-red-700 hover:bg-red-50 transition"
              >
                Delete
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="prose prose-lg max-w-none">
          <div className="p-6 rounded-2xl bg-white border border-surface-200 whitespace-pre-wrap text-surface-700 leading-relaxed">
            {currentJournal.raw_text}
          </div>
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

        {/* Feedback placeholder */}
        <div className="mt-8 p-6 rounded-2xl bg-primary-50/50 border border-primary-100">
          <h2 className="font-semibold text-primary-800 mb-2">Agent Feedback</h2>
          <p className="text-sm text-primary-600/70">
            AI-powered feedback will appear here after Phase 3 is implemented.
          </p>
        </div>
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
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </HashRouter>
  )
}

export default TabsApp
