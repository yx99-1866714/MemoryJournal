import { useEffect, useState } from "react"

import { apiGetJournalDates } from "~lib/api"

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
]

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

interface Props {
  onDateSelect: (year: number, month: number, day: number) => void
  selectedDate: { year: number; month: number; day: number } | null
}

export default function Calendar({ onDateSelect, selectedDate }: Props) {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1) // 1-indexed
  const [activeDays, setActiveDays] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)

  // Fetch journal dates for current month
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    apiGetJournalDates(year, month)
      .then((days) => {
        if (!cancelled) setActiveDays(new Set(days))
      })
      .catch(() => {
        if (!cancelled) setActiveDays(new Set())
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [year, month])

  // Calendar grid calculation
  const firstDay = new Date(year, month - 1, 1).getDay() // 0=Sun
  const daysInMonth = new Date(year, month, 0).getDate()

  const prevMonth = () => {
    if (month === 1) {
      setYear(year - 1)
      setMonth(12)
    } else {
      setMonth(month - 1)
    }
  }

  const nextMonth = () => {
    if (month === 12) {
      setYear(year + 1)
      setMonth(1)
    } else {
      setMonth(month + 1)
    }
  }

  const isSelected = (day: number) =>
    selectedDate?.year === year && selectedDate?.month === month && selectedDate?.day === day

  const isToday = (day: number) =>
    year === today.getFullYear() && month === today.getMonth() + 1 && day === today.getDate()

  return (
    <div className="bg-white rounded-2xl border border-surface-200 p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-center gap-4 mb-4">
        {/* Month selector */}
        <div className="flex items-center gap-1.5">
          <h3 className="font-semibold text-surface-800 w-24 text-center">
            {MONTH_NAMES[month - 1]}
          </h3>
          <div className="flex flex-col gap-0.5">
            <button
              onClick={nextMonth}
              className="w-5 h-4 rounded flex items-center justify-center text-surface-400 hover:bg-surface-100 hover:text-primary-600 transition text-[10px] leading-none"
            >
              ▲
            </button>
            <button
              onClick={prevMonth}
              className="w-5 h-4 rounded flex items-center justify-center text-surface-400 hover:bg-surface-100 hover:text-primary-600 transition text-[10px] leading-none"
            >
              ▼
            </button>
          </div>
        </div>

        {/* Year selector */}
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-surface-800 w-12 text-center">{year}</span>
          <div className="flex flex-col gap-0.5">
            <button
              onClick={() => setYear(year + 1)}
              className="w-5 h-4 rounded flex items-center justify-center text-surface-400 hover:bg-surface-100 hover:text-primary-600 transition text-[10px] leading-none"
            >
              ▲
            </button>
            <button
              onClick={() => setYear(year - 1)}
              className="w-5 h-4 rounded flex items-center justify-center text-surface-400 hover:bg-surface-100 hover:text-primary-600 transition text-[10px] leading-none"
            >
              ▼
            </button>
          </div>
        </div>
      </div>

      {/* Day labels */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {DAY_LABELS.map((d) => (
          <div key={d} className="text-center text-xs font-medium text-surface-400 py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7 gap-1">
        {/* Empty cells for offset */}
        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`empty-${i}`} className="h-9" />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1
          const hasJournal = activeDays.has(day)
          const selected = isSelected(day)
          const todayMark = isToday(day)

          return (
            <button
              key={day}
              onClick={() => hasJournal && onDateSelect(year, month, day)}
              disabled={!hasJournal}
              className={`
                h-9 rounded-lg text-sm font-medium relative transition-all duration-150
                ${selected
                  ? "bg-primary-500 text-white shadow-md shadow-primary-500/20"
                  : hasJournal
                    ? "bg-primary-50 text-primary-700 hover:bg-primary-100 hover:scale-105 cursor-pointer"
                    : "text-surface-300 cursor-default"
                }
                ${todayMark && !selected ? "ring-2 ring-primary-300 ring-offset-1" : ""}
              `}
            >
              {day}
              {hasJournal && !selected && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary-400" />
              )}
            </button>
          )
        })}
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="text-center text-xs text-surface-400 mt-2 animate-pulse">
          Loading...
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-surface-100">
        <div className="flex items-center gap-1.5 text-xs text-surface-400">
          <span className="w-3 h-3 rounded bg-primary-50 border border-primary-200" />
          Has entries
        </div>
        <div className="flex items-center gap-1.5 text-xs text-surface-400">
          <span className="w-3 h-3 rounded ring-2 ring-primary-300" />
          Today
        </div>
      </div>
    </div>
  )
}
