export { }

// Background service worker
// Handles extension lifecycle events and task reminders

// const API_BASE = "http://localhost:8000"
const API_BASE = process.env.NODE_ENV === "development"
  ? "http://localhost:8000"
  : "https://memoryjournal.onrender.com"
const ALARM_NAME = "check-reminders"
const CHECK_INTERVAL_MINUTES = 30

// ── Setup ────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  console.log("Memory Journal extension installed")
  // Create recurring alarm for reminder checks
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: CHECK_INTERVAL_MINUTES })
  // Run an initial check shortly after install
  chrome.alarms.create("initial-reminder-check", { delayInMinutes: 1 })
})

// Also set alarm on startup (after browser restart)
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: CHECK_INTERVAL_MINUTES })
  chrome.alarms.create("initial-reminder-check", { delayInMinutes: 1 })
})

// ── Alarm Handler ────────────────────────────────────

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_NAME || alarm.name === "initial-reminder-check") {
    await checkReminders()
    await checkUnreadMessages()
  }
})

// ── Message Handler (from frontend) ─────────────────

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "journal-submitted") {
    // Schedule unread checks at 15s, 30s, and 60s to catch agent check-ins
    // as they finish generating after journal processing
    setTimeout(() => checkUnreadMessages(), 15_000)
    setTimeout(() => checkUnreadMessages(), 30_000)
    setTimeout(() => checkUnreadMessages(), 60_000)
  }
})

// ── Notification Click Handler ───────────────────────

chrome.notifications.onClicked.addListener((notificationId) => {
  // Open the dashboard when a notification is clicked
  chrome.tabs.create({
    url: chrome.runtime.getURL("/tabs/index.html"),
  })
  chrome.notifications.clear(notificationId)
})

// ── Reminder Check Logic ─────────────────────────────

async function checkReminders() {
  try {
    const stored = await chrome.storage.local.get("token")
    const token = stored.token as string | undefined
    if (!token) {
      chrome.action.setBadgeText({ text: "" })
      return
    }

    const res = await fetch(`${API_BASE}/goals/reminders`, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    })

    if (!res.ok) {
      console.warn("Reminder check failed:", res.status)
      return
    }

    const data = await res.json()
    const reminders = data.reminders as Array<{
      id: string
      title: string
      due_at: string | null
      urgency: "overdue" | "today" | "tomorrow"
      goal_id: string | null
    }>

    // Send Chrome notifications for each reminder
    const icons = chrome.runtime.getManifest().icons || {}
    const iconPath = icons["128"] || icons["64"] || icons["48"] || icons["32"] || icons["16"]
    // iconUrl is REQUIRED – use a 1px transparent PNG as fallback
    const iconUrl = iconPath
      ? chrome.runtime.getURL(iconPath)
      : "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    console.log("Notification icon URL:", iconUrl)

    for (const reminder of reminders) {
      const urgencyLabel =
        reminder.urgency === "overdue"
          ? "⚠️ OVERDUE"
          : reminder.urgency === "today"
            ? "📅 Due Today"
            : "🔔 Due Tomorrow"

      const dueStr = reminder.due_at
        ? new Date(reminder.due_at).toLocaleDateString()
        : ""

      const notifId = `reminder-${reminder.id}`
      chrome.notifications.create(notifId, {
        type: "basic",
        iconUrl,
        title: `${urgencyLabel}: ${reminder.title}`,
        message: dueStr ? `Due: ${dueStr}` : "No specific deadline",
        priority: reminder.urgency === "overdue" ? 2 : 1,
      }, (createdId) => {
        if (chrome.runtime.lastError) {
          console.error(`Notification "${notifId}" failed:`, chrome.runtime.lastError.message)
        } else {
          console.log(`Notification "${createdId}" created successfully`)
        }
      })
    }

    console.log(`Reminder check: ${reminders.length} reminder(s) sent`)
  } catch (err) {
    console.warn("Reminder check error:", err)
  }
}

// ── Unread Messages Check ────────────────────────────

let previousUnreadTotal = 0

async function checkUnreadMessages() {
  try {
    const stored = await chrome.storage.local.get("token")
    const token = stored.token as string | undefined
    if (!token) return

    const res = await fetch(`${API_BASE}/agents/unread-total`, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    })

    if (!res.ok) return

    const data = await res.json()
    const unreadTotal = data.unread_total as number

    // Send notification if unread count increased (new agent check-in)
    if (unreadTotal > previousUnreadTotal) {
      const newCount = unreadTotal - previousUnreadTotal
      const icons = chrome.runtime.getManifest().icons || {}
      const iconPath = icons["128"] || icons["64"] || icons["48"] || icons["32"] || icons["16"]
      const iconUrl = iconPath
        ? chrome.runtime.getURL(iconPath)
        : "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

      chrome.notifications.create(`agent-checkin-${Date.now()}`, {
        type: "basic",
        iconUrl,
        title: "💬 New message from your companion",
        message: newCount === 1
          ? "An agent has sent you a check-in message"
          : `${newCount} new check-in messages from your agents`,
        priority: 1,
      }, (createdId) => {
        if (chrome.runtime.lastError) {
          console.error("Agent notification failed:", chrome.runtime.lastError.message)
        } else {
          console.log(`Agent notification "${createdId}" created`)
        }
      })
    }
    previousUnreadTotal = unreadTotal

    // Update badge with unread count
    if (unreadTotal > 0) {
      chrome.action.setBadgeText({ text: String(unreadTotal) })
      chrome.action.setBadgeBackgroundColor({ color: "#EF4444" }) // red
    } else {
      // Only clear badge if no reminders either
      chrome.action.setBadgeText({ text: "" })
    }

    console.log(`Unread check: ${unreadTotal} unread message(s)`)
  } catch (err) {
    console.warn("Unread check error:", err)
  }
}
