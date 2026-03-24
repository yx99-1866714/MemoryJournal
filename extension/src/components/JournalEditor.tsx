import { useCallback, useEffect, useRef, useState } from "react"

import { saveDraft, deleteDraft } from "~lib/storage"
import type { JournalDraft, SourceSurface } from "~lib/types"
import { useJournalStore } from "~store/journalStore"

const MOODS = ["😊", "😌", "😔", "😤", "😰", "🤔", "😴", "🎉", "💪", "❤️"]

interface Props {
  sourceSurface: SourceSurface
  existingDraft?: JournalDraft
  onSaved?: (journalId: string) => void
  compact?: boolean
}

export default function JournalEditor({ sourceSurface, existingDraft, onSaved, compact = false }: Props) {
  const draftId = useRef(existingDraft?.id || crypto.randomUUID())
  const [title, setTitle] = useState(existingDraft?.title || "")
  const [content, setContent] = useState(existingDraft?.content || "")
  const [mood, setMood] = useState<string | null>(existingDraft?.mood_label || null)
  const [saving, setSaving] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  const { createJournal, loading, error } = useJournalStore()

  // Auto-save draft to IndexedDB every 3 seconds on changes
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const saveDraftLocal = useCallback(async () => {
    if (!content.trim()) return
    await saveDraft({
      id: draftId.current,
      title,
      content,
      mood_label: mood,
      source_surface: sourceSurface,
      updated_at: Date.now(),
    })
  }, [title, content, mood, sourceSurface])

  useEffect(() => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current)
    autoSaveTimer.current = setTimeout(saveDraftLocal, 3000)
    return () => {
      if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current)
    }
  }, [title, content, mood, saveDraftLocal])

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0

  const handleSubmit = async () => {
    if (!content.trim()) return
    setSaving(true)
    try {
      const journal = await createJournal({
        title: title || undefined,
        content,
        submit: true,
        source_surface: sourceSurface,
        mood_label: mood || undefined,
      })
      await deleteDraft(draftId.current)
      setSubmitSuccess(true)
      onSaved?.(journal.id)
      setTimeout(() => setSubmitSuccess(false), 2000)
      // Notify background service worker to start checking for agent check-ins
      try { chrome.runtime.sendMessage({ type: "journal-submitted" }) } catch {}
    } catch {
      // error handled by store
    } finally {
      setSaving(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!content.trim()) return
    setSaving(true)
    try {
      await createJournal({
        title: title || undefined,
        content,
        submit: false,
        source_surface: sourceSurface,
        mood_label: mood || undefined,
      })
      await deleteDraft(draftId.current)
    } catch {
      // error handled by store
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={`flex flex-col gap-4 ${compact ? "" : "max-w-3xl mx-auto"}`}>
      {/* Title */}
      {!compact && (
        <input
          type="text"
          placeholder="Give your entry a title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-4 py-3 rounded-xl bg-surface-100 border border-surface-200 text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-400/40 focus:border-transparent text-lg font-medium transition"
        />
      )}

      {/* Editor */}
      <div className="relative">
        <textarea
          placeholder="What's on your mind today?"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={compact ? 6 : 14}
          className="w-full px-4 py-3 rounded-xl bg-surface-100 border border-surface-200 text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-primary-400/40 focus:border-transparent resize-y leading-relaxed transition"
        />
        <div className="absolute bottom-3 right-4 text-xs text-surface-400">
          {wordCount} {wordCount === 1 ? "word" : "words"}
        </div>
      </div>

      {/* Mood picker */}
      <div>
        <p className="text-sm text-surface-500 mb-2">How are you feeling?</p>
        <div className="flex gap-2 flex-wrap">
          {MOODS.map((m) => (
            <button
              key={m}
              onClick={() => setMood(mood === m ? null : m)}
              className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl transition-all duration-200 ${
                mood === m
                  ? "bg-primary-100 ring-2 ring-primary-400 scale-110"
                  : "bg-surface-100 hover:bg-surface-200 hover:scale-105"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Success feedback */}
      {submitSuccess && (
        <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm flex items-center gap-2">
          <span>✓</span> Journal submitted successfully!
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        {!compact && (
          <button
            onClick={handleSaveDraft}
            disabled={saving || loading || !content.trim()}
            className="px-5 py-2.5 rounded-xl border border-surface-300 text-surface-600 hover:bg-surface-100 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save Draft
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={saving || loading || !content.trim()}
          className="px-6 py-2.5 rounded-xl bg-primary-500 hover:bg-primary-400 text-white font-medium shadow-lg shadow-primary-500/25 hover:shadow-primary-400/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Submitting..." : "Submit Journal"}
        </button>
      </div>
    </div>
  )
}
