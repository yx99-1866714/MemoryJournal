import { useEffect, useState } from "react"

import { apiGetJournalFeedback, apiGetJournalStatus } from "~lib/api"
import type { Feedback, ProcessingStatus } from "~lib/types"

interface Props {
  journalId: string
  journalStatus: string
}

const SECTION_LABELS: Record<string, { emoji: string; label: string }> = {
  today_summary: { emoji: "📝", label: "Today's Summary" },
  pattern_connection: { emoji: "🔗", label: "Patterns & Connections" },
  supportive_observation: { emoji: "💛", label: "Observation" },
  next_step: { emoji: "🚀", label: "Next Step" },
  reflection_question: { emoji: "🤔", label: "Reflection Question" },
  goals_identified: { emoji: "🎯", label: "Goals Identified" },
  progress_update: { emoji: "📊", label: "Progress Update" },
  accountability_question: { emoji: "✅", label: "Accountability Check" },
  emotional_reflection: { emoji: "💭", label: "Emotional Reflection" },
  compassionate_reflection: { emoji: "🌸", label: "Compassionate Reflection" },
  self_care_suggestion: { emoji: "🫶", label: "Self-Care Suggestion" },
  gentle_question: { emoji: "🕊️", label: "Gentle Question" },
}

const AGENT_DISPLAY: Record<string, { icon: string; name: string }> = {
  reflection_coach: { icon: "🪞", name: "Reflection Coach" },
  goal_secretary: { icon: "📋", name: "Goal Secretary" },
  supportive_friend: { icon: "💛", name: "Supportive Friend" },
  inner_caregiver: { icon: "🤗", name: "Inner Caregiver" },
}

const STATUS_MESSAGES: Record<string, { emoji: string; text: string }> = {
  submitted: { emoji: "📤", text: "Journal submitted, starting processing..." },
  processing: { emoji: "⏳", text: "Processing your journal..." },
  queued: { emoji: "⏳", text: "Extracting memories..." },
  completed: { emoji: "🧠", text: "Generating feedback..." },
}

export default function FeedbackCard({ journalId, journalStatus }: Props) {
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    let pollTimer: ReturnType<typeof setTimeout>

    const fetchStatus = async () => {
      try {
        const s = await apiGetJournalStatus(journalId)
        if (cancelled) return
        setStatus(s)

        if (s.has_feedback) {
          const res = await apiGetJournalFeedback(journalId)
          if (!cancelled && res.feedback.length > 0) {
            setFeedback(res.feedback[0])
          }
          setLoading(false)
        } else if (s.status === "processed" || s.status === "failed" || s.status === "draft") {
          setLoading(false)
        } else {
          // Still processing — poll again
          pollTimer = setTimeout(fetchStatus, 3000)
        }
      } catch {
        if (!cancelled) setLoading(false)
      }
    }

    fetchStatus()

    return () => {
      cancelled = true
      clearTimeout(pollTimer)
    }
  }, [journalId])

  // Draft journals don't have feedback
  if (journalStatus === "draft") return null

  // Still loading / polling
  if (loading && !feedback) {
    const statusMsg = STATUS_MESSAGES[status?.evermemos_status || status?.status || "submitted"]
    return (
      <div className="mt-6 p-5 rounded-2xl bg-primary-50 border border-primary-100 animate-pulse">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{statusMsg?.emoji || "⏳"}</span>
          <div>
            <p className="font-medium text-primary-700">{statusMsg?.text || "Processing..."}</p>
            <p className="text-xs text-primary-400 mt-1">This usually takes 10–30 seconds</p>
          </div>
        </div>
      </div>
    )
  }

  // Failed
  if (status?.status === "failed" && !feedback) {
    return (
      <div className="mt-6 p-5 rounded-2xl bg-red-50 border border-red-100">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <p className="font-medium text-red-700">
            Processing failed. Your journal is saved — feedback will be retried.
          </p>
        </div>
      </div>
    )
  }

  // No feedback available
  if (!feedback) return null

  // Render feedback as plain text
  return (
    <div className="mt-6">
      <div className="p-5 rounded-2xl bg-white border border-surface-200">
        <p className="text-surface-700 leading-relaxed whitespace-pre-wrap">
          {feedback.response_text}
        </p>
      </div>
    </div>
  )
}
