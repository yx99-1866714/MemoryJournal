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

  // Render structured feedback
  const sections = feedback.response_json
  return (
    <div className="mt-6 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">🪞</span>
        <h3 className="text-lg font-semibold text-surface-800">Reflection Coach</h3>
        {feedback.model_name && (
          <span className="text-xs text-surface-400 ml-auto">{feedback.model_name}</span>
        )}
      </div>

      {sections ? (
        Object.entries(SECTION_LABELS).map(([key, { emoji, label }]) => {
          const content = sections[key as keyof typeof sections]
          if (!content) return null
          return (
            <div
              key={key}
              className="p-4 rounded-xl bg-white border border-surface-200 hover:border-primary-200 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <span>{emoji}</span>
                <span className="text-sm font-semibold text-surface-600">{label}</span>
              </div>
              <p className="text-surface-700 leading-relaxed">{content}</p>
            </div>
          )
        })
      ) : (
        <div className="p-4 rounded-xl bg-white border border-surface-200">
          <p className="text-surface-700 leading-relaxed whitespace-pre-wrap">
            {feedback.response_text}
          </p>
        </div>
      )}
    </div>
  )
}
