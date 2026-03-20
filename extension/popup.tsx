import { useEffect } from "react"

import "~src/style.css"

import { useAuthStore } from "~store/authStore"

function Popup() {
  const { user, loading, init } = useAuthStore()

  useEffect(() => {
    init()
  }, [])

  const openFullPage = () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html") })
  }

  const openNewJournal = () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("/tabs/index.html#/journal/new") })
  }

  const openSidePanel = () => {
    // Side panel opens via the action in manifest; this is a fallback
    chrome.sidePanel?.open?.({ windowId: undefined as any })
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
          <span>📚</span> View History
        </button>
        <button
          onClick={openSidePanel}
          className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all flex items-center justify-center gap-2 border border-white/10"
        >
          <span>📝</span> Quick Entry (Side Panel)
        </button>
      </div>

      <div className="mt-4 pt-4 border-t border-white/10">
        <p className="text-xs text-primary-200/50 text-center">
          Today's reminders coming soon
        </p>
      </div>
    </div>
  )
}

export default Popup
