import { useEffect, useState, type ReactNode } from "react"

import { apiGetUnreadTotal } from "~lib/api"
import { useAuthStore } from "~store/authStore"

interface Props {
  children: ReactNode
  title?: string
  showNav?: boolean
}

const navItems = [
  { label: "Home", path: "/tabs/index.html", icon: "🏠" },
  { label: "New Journal", path: "/tabs/index.html#/journal/new", icon: "✏️" },
  { label: "History", path: "/tabs/index.html#/history", icon: "📚" },
  { label: "Goals", path: "/tabs/index.html#/goals", icon: "🎯" },
  { label: "Chat", path: "/tabs/index.html#/chat", icon: "💬" },
  { label: "Agents", path: "/tabs/index.html#/agents", icon: "🤖" },
  { label: "Settings", path: "/tabs/index.html#/settings", icon: "⚙️" },
]

export default function Layout({ children, title, showNav = true }: Props) {
  const { user, logout } = useAuthStore()
  const [unreadTotal, setUnreadTotal] = useState(0)

  // Poll unread count periodically so badge stays in sync
  useEffect(() => {
    if (!user) return

    const fetchUnread = () => {
      apiGetUnreadTotal()
        .then((res) => setUnreadTotal(res.unread_total))
        .catch(() => {})
    }

    fetchUnread() // initial fetch
    const interval = setInterval(fetchUnread, 15_000) // every 15s

    // Also refresh on route navigation
    const onHashChange = () => fetchUnread()
    window.addEventListener("hashchange", onHashChange)

    return () => {
      clearInterval(interval)
      window.removeEventListener("hashchange", onHashChange)
    }
  }, [user])

  const navigateTo = (path: string) => {
    window.location.href = chrome.runtime.getURL(path)
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      {showNav && (
        <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200">
          <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigateTo("/tabs/index.html")}
                className="flex items-center gap-2 text-lg font-bold text-primary-700 hover:text-primary-600 transition"
              >
                <span className="text-xl">📓</span>
                EverMind
              </button>
              <nav className="hidden sm:flex items-center gap-1 ml-4">
                {navItems.map((item) => (
                  <button
                    key={item.path}
                    onClick={() => navigateTo(item.path)}
                    className="relative px-3 py-1.5 rounded-lg text-sm text-surface-600 hover:text-primary-600 hover:bg-primary-50 transition-all"
                  >
                    <span className="mr-1">{item.icon}</span>
                    {item.label}
                    {item.label === "Chat" && unreadTotal > 0 && (
                      <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
                        {unreadTotal > 9 ? "9+" : unreadTotal}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </div>
            <div className="flex items-center gap-3">
              {user && (
                <>
                  <span className="text-sm text-surface-500 hidden sm:block">
                    {user.name}
                  </span>
                  <button
                    onClick={() => logout()}
                    className="text-sm px-3 py-1.5 rounded-lg text-surface-500 hover:text-red-600 hover:bg-red-50 transition-all"
                  >
                    Sign Out
                  </button>
                </>
              )}
            </div>
          </div>
        </header>
      )}

      {/* Page content */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        {title && (
          <h1 className="text-2xl font-bold text-surface-900 mb-6">{title}</h1>
        )}
        {children}
      </main>
    </div>
  )
}
