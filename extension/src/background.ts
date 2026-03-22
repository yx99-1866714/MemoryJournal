export {}

// Background service worker
// Handles extension lifecycle events and task reminders

const API_BASE = "http://localhost:8000"
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
  }
})

// ── Notification Click Handler ───────────────────────

chrome.notifications.onClicked.addListener((notificationId) => {
  // Open the Goals dashboard when a reminder notification is clicked
  chrome.tabs.create({
    url: chrome.runtime.getURL("/tabs/index.html#/goals"),
  })
  chrome.notifications.clear(notificationId)
})

// ── Reminder Check Logic ─────────────────────────────

async function checkReminders() {
  try {
    const stored = await chrome.storage.local.get("token")
    const token = stored.token as string | undefined
    if (!token) {
      // Not logged in, clear badge
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

    // Update badge count
    if (reminders.length > 0) {
      chrome.action.setBadgeText({ text: String(reminders.length) })
      chrome.action.setBadgeBackgroundColor({ color: "#EF4444" }) // red
    } else {
      chrome.action.setBadgeText({ text: "" })
    }

    // Send Chrome notifications for each reminder
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

      chrome.notifications.create(`reminder-${reminder.id}`, {
        type: "basic",
        iconUrl: chrome.runtime.getURL("assets/icon.png"),
        title: `${urgencyLabel}: ${reminder.title}`,
        message: dueStr ? `Due: ${dueStr}` : "No specific deadline",
        priority: reminder.urgency === "overdue" ? 2 : 1,
        requireInteraction: reminder.urgency === "overdue",
      })
    }

    console.log(`Reminder check: ${reminders.length} reminder(s) sent`)
  } catch (err) {
    console.warn("Reminder check error:", err)
  }
}
