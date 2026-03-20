import { useEffect } from "react"

import "~src/style.css"

import AuthForm from "~components/AuthForm"
import JournalEditor from "~components/JournalEditor"
import { useAuthStore } from "~store/authStore"

function SidePanel() {
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
    <div className="min-h-screen bg-surface-50">
      {/* Compact header */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📓</span>
            <h1 className="text-sm font-bold text-primary-700">Quick Entry</h1>
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

      {/* Compact editor */}
      <div className="p-4">
        <JournalEditor sourceSurface="sidepanel" compact />
      </div>
    </div>
  )
}

export default SidePanel
