import type { Journal } from "~lib/types"

interface Props {
  journal: Journal
  onClick?: () => void
}

const statusColors: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700",
  submitted: "bg-blue-100 text-blue-700",
  processed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
}

export default function JournalCard({ journal, onClick }: Props) {
  const date = new Date(journal.created_at)
  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  })
  const formattedTime = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  })

  const preview = journal.raw_text.length > 150
    ? journal.raw_text.slice(0, 150) + "..."
    : journal.raw_text

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl bg-white border border-surface-200 hover:border-primary-300 hover:shadow-md hover:shadow-primary-500/5 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-surface-800 truncate group-hover:text-primary-700 transition">
            {journal.title || "Untitled Entry"}
          </h3>
          <p className="text-xs text-surface-400 mt-0.5">
            {formattedDate} at {formattedTime}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {journal.mood_label && (
            <span className="text-lg">{journal.mood_label}</span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[journal.status] || "bg-surface-100 text-surface-600"}`}>
            {journal.status}
          </span>
        </div>
      </div>
      <p className="text-sm text-surface-500 leading-relaxed line-clamp-2">
        {preview}
      </p>
      {journal.word_count && (
        <p className="text-xs text-surface-400 mt-2">
          {journal.word_count} words
        </p>
      )}
      {journal.tags && journal.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {journal.tags.map((tag) => (
            <span
              key={tag.id}
              className="text-[10px] px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 font-medium"
            >
              #{tag.name}
            </span>
          ))}
        </div>
      )}
    </button>
  )
}
