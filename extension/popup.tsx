import { useEffect, useState } from "react"

import "~src/style.css"

import type { GoalsSummary } from "~lib/api"
import { apiGetGoalsSummary, apiGetUnreadTotal } from "~lib/api"
import { useAuthStore } from "~store/authStore"

function Popup() {
  const { user, loading, init } = useAuthStore()
  const [summary, setSummary] = useState<GoalsSummary | null>(null)
  const [unreadTotal, setUnreadTotal] = useState(0)

  useEffect(() => {
    init()
  }, [])

  useEffect(() => {
    if (user) {
      apiGetGoalsSummary()
        .then(setSummary)
        .catch(() => {})
      apiGetUnreadTotal()
        .then((res) => setUnreadTotal(res.unread_total))
        .catch(() => {})
    }
  }, [user])

  const openFullPage = () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html") })
  }

  const openNewJournal = () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html#/journal/new") })
  }

  const openGoals = () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html#/goals") })
  }

  const openSidePanel = async () => {
    const win = await chrome.windows.getCurrent()
    await chrome.sidePanel.setOptions({ path: "sidepanel.html" })
    chrome.sidePanel?.open?.({ windowId: win.id! })
  }

  const openChatPanel = async () => {
    const win = await chrome.windows.getCurrent()
    await chrome.sidePanel.setOptions({ path: "sidepanel.html#chat" })
    chrome.sidePanel?.open?.({ windowId: win.id! })
  }

  if (loading) {
    return (
      <div className="w-80 h-48 flex items-center justify-center bg-gradient-to-br from-primary-800 to-primary-900">
        <div className="animate-pulse text-primary-200">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="w-80 p-6 bg-gradient-to-br from-primary-800 to-primary-900">
        <div className="text-center">
          <span className="text-4xl block mb-3">📓</span>
          <h1 className="text-lg font-bold text-white mb-2">Memory Journal</h1>
          <p className="text-primary-200/70 text-sm mb-4">Sign in to start journaling</p>
          <button
            onClick={openFullPage}
            className="w-full py-2.5 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium transition shadow-lg"
          >
            Sign In / Sign Up
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 bg-gradient-to-br from-primary-800 to-primary-900 p-6">
      <div className="flex items-center gap-3 mb-5">
        <span className="text-2xl">📓</span>
        <div>
          <h1 className="text-base font-bold text-white">Memory Journal</h1>
          <p className="text-xs text-primary-200/70">Hi, {user.name}</p>
        </div>
      </div>

      {/* Goal/Task Summary Widget */}
      {summary && (summary.active_goals > 0 || summary.open_tasks > 0) && (
        <div
          onClick={openGoals}
          className="mb-4 p-3 rounded-xl bg-white/10 border border-white/10 cursor-pointer hover:bg-white/15 transition"
        >
          <div className="flex gap-4 mb-2">
            <div className="text-center flex-1">
              <div className="text-xl font-bold text-white">{summary.active_goals}</div>
              <div className="text-[10px] text-primary-200/60 uppercase tracking-wide">Goals</div>
            </div>
            <div className="w-px bg-white/15" />
            <div className="text-center flex-1">
              <div className="text-xl font-bold text-white">{summary.open_tasks}</div>
              <div className="text-[10px] text-primary-200/60 uppercase tracking-wide">Tasks</div>
            </div>
          </div>
          {/* Urgent task badges */}
          {(summary.overdue_tasks > 0 || summary.due_today_tasks > 0) && (
            <div className="flex gap-2 mt-2 pt-2 border-t border-white/10">
              {summary.overdue_tasks > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 font-medium">
                  ⚠️ {summary.overdue_tasks} overdue
                </span>
              )}
              {summary.due_today_tasks > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-medium">
                  📅 {summary.due_today_tasks} due today
                </span>
              )}
            </div>
          )}
          {summary.recent_tasks.length > 0 && (
            <div className="space-y-1 mt-2 pt-2 border-t border-white/10">
              {summary.recent_tasks.slice(0, 3).map((t) => (
                <div key={t.id} className="flex items-center gap-2 text-xs text-primary-100/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                  <span className="truncate">{t.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="space-y-2.5">
        <button
          onClick={openNewJournal}
          className="w-full py-3 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium transition-all shadow-lg shadow-primary-500/25 flex items-center justify-center gap-2"
        >
          <span>✏️</span> New Journal Entry
        </button>
        <button
          onClick={openFullPage}
          className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all flex items-center justify-center gap-2 border border-white/10"
        >
          <span>📊</span> Full Dashboard
        </button>
        <button
          onClick={openGoals}
          className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all flex items-center justify-center gap-2 border border-white/10"
        >
          <span>🎯</span> Goals & Tasks
        </button>
        <button
          onClick={openSidePanel}
          className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all flex items-center justify-center gap-2 border border-white/10"
        >
          <span>📝</span> Quick Entry (Side Panel)
        </button>
        <button
          onClick={openChatPanel}
          className="relative w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all flex items-center justify-center gap-2 border border-white/10"
        >
          {unreadTotal > 0 && (
            <span className="absolute top-1.5 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow">
              {unreadTotal > 9 ? "9+" : unreadTotal}
            </span>
          )}
          <span>💬</span> AI Chat (Side Panel)
        </button>
      </div>
    </div>
  )
}

export default Popup
