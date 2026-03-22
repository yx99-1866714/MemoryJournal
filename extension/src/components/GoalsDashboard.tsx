import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"

import type { GoalItem, TaskItem } from "~lib/api"
import { apiDeleteGoal, apiDeleteTask, apiGetGoals, apiGetTasks, apiUpdateGoal, apiUpdateGoalStatus, apiUpdateTask, apiUpdateTaskStatus } from "~lib/api"

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-100 text-emerald-700",
  completed: "bg-blue-100 text-blue-700",
  paused: "bg-amber-100 text-amber-700",
  abandoned: "bg-surface-100 text-surface-500",
  open: "bg-emerald-100 text-emerald-700",
  dismissed: "bg-surface-100 text-surface-500",
}

function RecurrenceBadge({ recurrence, frequency }: { recurrence: string; frequency: string | null }) {
  if (recurrence === "recurring") {
    return (
      <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-violet-100 text-violet-700">
        🔄 {frequency || "recurring"}
      </span>
    )
  }
  return (
    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-surface-100 text-surface-500">
      📌 one-time
    </span>
  )
}

function DueDateBadge({ dueAt }: { dueAt: string | null }) {
  if (!dueAt) {
    return (
      <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-surface-100 text-surface-400">
        No deadline
      </span>
    )
  }
  const due = new Date(dueAt)
  const now = new Date()
  const diffDays = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  const label = due.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  const isOverdue = diffDays < 0
  const isSoon = diffDays >= 0 && diffDays <= 3
  const colorClass = isOverdue
    ? "bg-red-100 text-red-700"
    : isSoon
      ? "bg-amber-100 text-amber-700"
      : "bg-blue-100 text-blue-700"
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${colorClass}`}>
      📅 {isOverdue ? "Overdue" : `Due ${label}`}
    </span>
  )
}

export default function GoalsDashboard() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState<GoalItem[]>([])
  const [standaloneTasks, setStandaloneTasks] = useState<TaskItem[]>([])
  const [tab, setTab] = useState<"goals" | "tasks">("goals")
  const [loading, setLoading] = useState(true)

  const reload = async () => {
    try {
      const [goalsRes, tasksRes] = await Promise.all([
        apiGetGoals(),
        apiGetTasks(),
      ])
      setGoals(goalsRes.goals)
      // Standalone tasks are those not linked to a goal
      setStandaloneTasks(tasksRes.tasks.filter((t) => !t.goal_id))
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  const handleGoalStatus = async (goalId: string, status: string) => {
    await apiUpdateGoalStatus(goalId, status)
    reload()
  }

  const handleTaskStatus = async (taskId: string, status: string) => {
    await apiUpdateTaskStatus(taskId, status)
    reload()
  }

  const handleDeleteGoal = async (goalId: string) => {
    if (!confirm("Delete this goal and its tasks? This cannot be undone.")) return
    await apiDeleteGoal(goalId)
    reload()
  }

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("Delete this task? This cannot be undone.")) return
    await apiDeleteTask(taskId)
    reload()
  }

  const handleUpdateTask = async (taskId: string, data: { title?: string; due_at?: string | null }) => {
    await apiUpdateTask(taskId, data)
    reload()
  }

  const handleUpdateGoal = async (goalId: string, data: {
    title?: string; description?: string;
    recurrence?: string; recurrence_frequency?: string | null;
  }) => {
    await apiUpdateGoal(goalId, data)
    reload()
  }

  if (loading) {
    return <div className="text-center py-12 text-surface-400">Loading goals...</div>
  }

  const activeGoals = goals.filter((g) => g.status === "active")
  const completedGoals = goals.filter((g) => g.status !== "active")

  return (
    <div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-surface-100 p-1 rounded-xl">
        <button
          onClick={() => setTab("goals")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            tab === "goals"
              ? "bg-white text-surface-900 shadow-sm"
              : "text-surface-500 hover:text-surface-700"
          }`}
        >
          🎯 Goals ({activeGoals.length})
        </button>
        <button
          onClick={() => setTab("tasks")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            tab === "tasks"
              ? "bg-white text-surface-900 shadow-sm"
              : "text-surface-500 hover:text-surface-700"
          }`}
        >
          ✅ Tasks ({standaloneTasks.filter((t) => t.status === "open").length})
        </button>
      </div>

      {/* Goals Tab */}
      {tab === "goals" && (
        <div className="space-y-4">
          {activeGoals.length === 0 && completedGoals.length === 0 && (
            <div className="text-center py-12">
              <span className="text-4xl block mb-3">🎯</span>
              <p className="text-surface-400 text-sm">No goals yet — write a journal and mention your goals!</p>
            </div>
          )}
          {activeGoals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onStatusChange={handleGoalStatus}
              onTaskStatusChange={handleTaskStatus}
              onDeleteGoal={handleDeleteGoal}
              onDeleteTask={handleDeleteTask}
              onUpdateTask={handleUpdateTask}
              onUpdateGoal={handleUpdateGoal}
              onViewJournal={(id) => navigate(`/journal/${id}`)}
            />
          ))}
          {completedGoals.length > 0 && (
            <div className="mt-8">
              <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">
                Completed / Archived
              </h3>
              <div className="space-y-3 opacity-60">
                {completedGoals.map((goal) => (
                  <GoalCard
                    key={goal.id}
                    goal={goal}
                    onStatusChange={handleGoalStatus}
                    onTaskStatusChange={handleTaskStatus}
                    onDeleteGoal={handleDeleteGoal}
                    onDeleteTask={handleDeleteTask}
                    onUpdateTask={handleUpdateTask}
                    onUpdateGoal={handleUpdateGoal}
                    onViewJournal={(id) => navigate(`/journal/${id}`)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tasks Tab */}
      {tab === "tasks" && (
        <div className="space-y-2">
          {standaloneTasks.length === 0 && (
            <div className="text-center py-12">
              <span className="text-4xl block mb-3">✅</span>
              <p className="text-surface-400 text-sm">No standalone tasks — write a journal and mention things to do!</p>
            </div>
          )}
          {standaloneTasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              onStatusChange={handleTaskStatus}
              onDelete={handleDeleteTask}
              onUpdate={handleUpdateTask}
              onViewJournal={(id) => navigate(`/journal/${id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function GoalCard({
  goal,
  onStatusChange,
  onTaskStatusChange,
  onDeleteGoal,
  onDeleteTask,
  onUpdateTask,
  onUpdateGoal,
  onViewJournal,
}: {
  goal: GoalItem
  onStatusChange: (id: string, status: string) => void
  onTaskStatusChange: (id: string, status: string) => void
  onDeleteGoal: (id: string) => void
  onDeleteTask: (id: string) => void
  onUpdateTask: (id: string, data: { title?: string; due_at?: string | null }) => void
  onUpdateGoal: (id: string, data: { title?: string; description?: string; recurrence?: string; recurrence_frequency?: string | null }) => void
  onViewJournal: (id: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(goal.title)
  const [editDesc, setEditDesc] = useState(goal.description || "")
  const [editRecurrence, setEditRecurrence] = useState(goal.recurrence || "one_time")
  const [editFrequency, setEditFrequency] = useState(goal.recurrence_frequency || "")

  const handleSave = () => {
    onUpdateGoal(goal.id, {
      title: editTitle,
      description: editDesc,
      recurrence: editRecurrence,
      recurrence_frequency: editRecurrence === "recurring" ? (editFrequency || null) : null,
    })
    setEditing(false)
  }

  const handleCancel = () => {
    setEditTitle(goal.title)
    setEditDesc(goal.description || "")
    setEditRecurrence(goal.recurrence || "one_time")
    setEditFrequency(goal.recurrence_frequency || "")
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="rounded-xl bg-white border border-primary-200 overflow-hidden p-4 space-y-3">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="text-sm font-semibold px-2 py-1.5 rounded-lg border border-surface-200 focus:border-primary-400 focus:outline-none w-full"
          placeholder="Goal title..."
        />
        <textarea
          value={editDesc}
          onChange={(e) => setEditDesc(e.target.value)}
          className="text-sm px-2 py-1.5 rounded-lg border border-surface-200 focus:border-primary-400 focus:outline-none w-full resize-none"
          rows={2}
          placeholder="Description (optional)..."
        />
        <div className="flex items-center gap-3">
          <label className="text-xs text-surface-500">Recurrence:</label>
          <select
            value={editRecurrence}
            onChange={(e) => setEditRecurrence(e.target.value)}
            className="text-xs px-2 py-1 rounded-lg border border-surface-200 focus:outline-none"
          >
            <option value="one_time">One-time</option>
            <option value="recurring">Recurring</option>
          </select>
          {editRecurrence === "recurring" && (
            <select
              value={editFrequency}
              onChange={(e) => setEditFrequency(e.target.value)}
              className="text-xs px-2 py-1 rounded-lg border border-surface-200 focus:outline-none"
            >
              <option value="">Select frequency</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
          )}
          <div className="flex-1" />
          <button
            onClick={handleCancel}
            className="text-xs px-2.5 py-1 rounded-lg text-surface-500 hover:bg-surface-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-xs px-3 py-1 rounded-lg bg-primary-500 text-white hover:bg-primary-400 transition font-medium"
          >
            Save
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-white border border-surface-200 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-surface-900">{goal.title}</h3>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[goal.status] || ""}`}>
                {goal.status}
              </span>
              <RecurrenceBadge recurrence={goal.recurrence} frequency={goal.recurrence_frequency} />
            </div>
            {goal.description && (
              <p className="text-sm text-surface-500 mt-1">{goal.description}</p>
            )}
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setEditing(true)}
              className="text-xs px-2.5 py-1 rounded-lg bg-primary-50 text-primary-500 hover:bg-primary-100 transition"
            >
              ✏️
            </button>
            {goal.status === "active" && (
              <button
                onClick={() => onStatusChange(goal.id, "completed")}
                className="text-xs px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition"
              >
                Complete
              </button>
            )}
            {goal.status === "active" && (
              <button
                onClick={() => onStatusChange(goal.id, "abandoned")}
                className="text-xs px-2.5 py-1 rounded-lg bg-surface-50 text-surface-500 hover:bg-surface-100 transition"
              >
                Archive
              </button>
            )}
            {goal.status !== "active" && (
              <button
                onClick={() => onStatusChange(goal.id, "active")}
                className="text-xs px-2.5 py-1 rounded-lg bg-primary-50 text-primary-600 hover:bg-primary-100 transition"
              >
                Reactivate
              </button>
            )}
            <button
              onClick={() => onDeleteGoal(goal.id)}
              className="text-xs px-2.5 py-1 rounded-lg bg-red-50 text-red-500 hover:bg-red-100 transition"
            >
              🗑
            </button>
          </div>
        </div>

        {/* Source journal link */}
        {goal.source_journal_id && (
          <button
            onClick={() => onViewJournal(goal.source_journal_id!)}
            className="mt-2 text-xs text-primary-500 hover:text-primary-600 transition"
          >
            View source journal →
          </button>
        )}
      </div>

      {/* Nested tasks */}
      {goal.tasks.length > 0 && (
        <div className="border-t border-surface-100 bg-surface-50/50 px-4 py-2 space-y-1">
          {goal.tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              onStatusChange={onTaskStatusChange}
              onDelete={onDeleteTask}
              onUpdate={onUpdateTask}
              onViewJournal={onViewJournal}
              compact
            />
          ))}
        </div>
      )}
    </div>
  )
}

function TaskRow({
  task,
  onStatusChange,
  onDelete,
  onUpdate,
  onViewJournal,
  compact = false,
}: {
  task: TaskItem
  onStatusChange: (id: string, status: string) => void
  onDelete?: (id: string) => void
  onUpdate?: (id: string, data: { title?: string; due_at?: string | null }) => void
  onViewJournal: (id: string) => void
  compact?: boolean
}) {
  const isDone = task.status === "completed" || task.status === "dismissed"
  const [editing, setEditing] = useState(false)

  // Convert UTC date to local YYYY-MM-DD for the date picker
  const toLocalDateStr = (iso: string | null) => {
    if (!iso) return ""
    const d = new Date(iso)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, "0")
    const day = String(d.getDate()).padStart(2, "0")
    return `${y}-${m}-${day}`
  }

  const [editTitle, setEditTitle] = useState(task.title)
  const [editDueAt, setEditDueAt] = useState(toLocalDateStr(task.due_at))

  const handleSave = () => {
    if (!onUpdate) return
    onUpdate(task.id, {
      title: editTitle,
      due_at: editDueAt || null,
    })
    setEditing(false)
  }

  const handleCancel = () => {
    setEditTitle(task.title)
    setEditDueAt(toLocalDateStr(task.due_at))
    setEditing(false)
  }

  if (editing) {
    return (
      <div className={`flex flex-col gap-2 ${compact ? "py-1.5" : "p-3 rounded-xl bg-white border border-primary-200"}`}>
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="text-sm px-2 py-1 rounded-lg border border-surface-200 focus:border-primary-400 focus:outline-none w-full"
          placeholder="Task title..."
        />
        <div className="flex items-center gap-2">
          <label className="text-xs text-surface-500">Due:</label>
          <input
            type="date"
            value={editDueAt}
            onChange={(e) => setEditDueAt(e.target.value)}
            className="text-xs px-2 py-1 rounded-lg border border-surface-200 focus:border-primary-400 focus:outline-none"
          />
          {editDueAt && (
            <button onClick={() => setEditDueAt("")} className="text-xs text-surface-400 hover:text-red-500">
              Clear
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={handleCancel}
            className="text-xs px-2.5 py-1 rounded-lg text-surface-500 hover:bg-surface-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-xs px-3 py-1 rounded-lg bg-primary-500 text-white hover:bg-primary-400 transition font-medium"
          >
            Save
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`flex items-center gap-3 ${
        compact ? "py-1.5" : "p-3 rounded-xl bg-white border border-surface-200"
      }`}
    >
      <button
        onClick={() => onStatusChange(task.id, isDone ? "open" : "completed")}
        className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-all ${
          isDone
            ? "bg-emerald-500 border-emerald-500 text-white"
            : "border-surface-300 hover:border-emerald-400"
        }`}
      >
        {isDone && <span className="text-xs">✓</span>}
      </button>
      <span
        className={`flex-1 text-sm ${
          isDone ? "line-through text-surface-400" : "text-surface-700"
        }`}
      >
        {task.title}
      </span>
      <RecurrenceBadge recurrence={task.recurrence} frequency={task.recurrence_frequency} />
      <DueDateBadge dueAt={task.due_at ?? null} />
      {onUpdate && (
        <button
          onClick={() => setEditing(true)}
          className="text-xs w-6 h-6 rounded-md flex items-center justify-center text-surface-400 hover:text-primary-500 hover:bg-primary-50 transition"
          title="Edit task"
        >
          ✏️
        </button>
      )}
      {!compact && task.source_journal_id && (
        <button
          onClick={() => onViewJournal(task.source_journal_id!)}
          className="text-xs text-primary-400 hover:text-primary-600 transition"
        >
          source
        </button>
      )}
      {onDelete && (
        <button
          onClick={() => onDelete(task.id)}
          className="text-xs w-6 h-6 rounded-md flex items-center justify-center text-surface-400 hover:text-red-500 hover:bg-red-50 transition"
          title="Delete task"
        >
          🗑
        </button>
      )}
    </div>
  )
}
