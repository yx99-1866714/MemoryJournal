import type { Agent, AgentListResponse, AgentMessage, AgentRespondRequest, AgentThread, FeedbackListResponse, Journal, JournalListResponse, ProcessingStatus, Tag, TokenResponse, User } from "./types"
import { getStoredToken } from "./tokenStorage"

//const API_BASE = "http://localhost:8000"
const API_BASE = process.env.NODE_ENV === "development"
  ? "http://localhost:8000"
  : "https://memoryjournal.onrender.com"

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getStoredToken()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

// ---- Auth ----

export async function apiRegister(email: string, name: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, name, password }),
  })
}

export async function apiLogin(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function apiGetMe(): Promise<User> {
  return request<User>("/auth/me")
}

export async function apiRefreshToken(): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/refresh", { method: "POST" })
}

// ---- Journals ----

export async function apiCreateJournal(data: {
  title?: string
  content: string
  submit?: boolean
  source_surface?: string
  mood_label?: string
}): Promise<Journal> {
  return request<Journal>("/journals/", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function apiGetJournals(limit = 50, offset = 0): Promise<JournalListResponse> {
  return request<JournalListResponse>(`/journals/?limit=${limit}&offset=${offset}`)
}

export async function apiGetJournal(id: string): Promise<Journal> {
  return request<Journal>(`/journals/${id}`)
}

export async function apiUpdateJournal(id: string, data: {
  title?: string
  content?: string
  submit?: boolean
  mood_label?: string
}): Promise<Journal> {
  return request<Journal>(`/journals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function apiDeleteJournal(id: string): Promise<void> {
  return request<void>(`/journals/${id}`, { method: "DELETE" })
}

export async function apiGetJournalDates(year: number, month: number): Promise<number[]> {
  const tz = -new Date().getTimezoneOffset() // JS gives positive for west; we need the inverse
  return request<number[]>(`/journals/dates?year=${year}&month=${month}&tz_offset=${tz}`)
}

export async function apiGetJournalsByDate(year: number, month: number, day: number): Promise<JournalListResponse> {
  const tz = -new Date().getTimezoneOffset()
  return request<JournalListResponse>(`/journals/by-date?year=${year}&month=${month}&day=${day}&tz_offset=${tz}`)
}

// ---- Feedback (Phase 2) ----

export async function apiGetJournalFeedback(journalId: string): Promise<FeedbackListResponse> {
  return request<FeedbackListResponse>(`/journals/${journalId}/feedback`)
}

export async function apiGetJournalStatus(journalId: string): Promise<ProcessingStatus> {
  return request<ProcessingStatus>(`/journals/${journalId}/status`)
}

// ---- Agents (Phase 3) ----

export async function apiGetAgents(): Promise<AgentListResponse> {
  return request<AgentListResponse>("/agents/")
}

export async function apiAgentRespond(agentId: string, body: AgentRespondRequest): Promise<AgentMessage> {
  const payload = {
    ...body,
    tz_offset_minutes: new Date().getTimezoneOffset(),
  }
  return request<AgentMessage>(`/agents/${agentId}/respond`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function apiGetThread(agentId: string, journalId?: string): Promise<AgentThread | null> {
  const params = journalId ? `?journal_id=${journalId}` : ""
  return request<AgentThread | null>(`/agents/${agentId}/threads${params}`)
}

export async function apiClearThread(agentId: string, journalId?: string): Promise<void> {
  const params = journalId ? `?journal_id=${journalId}` : ""
  return request<void>(`/agents/${agentId}/threads${params}`, { method: "DELETE" })
}

export async function apiMarkThreadRead(agentId: string, journalId?: string): Promise<void> {
  const params = journalId ? `?journal_id=${journalId}` : ""
  return request<void>(`/agents/${agentId}/threads/read${params}`, { method: "POST" })
}

export async function apiGetUnreadTotal(): Promise<{ unread_total: number }> {
  return request<{ unread_total: number }>("/agents/unread-total")
}

// ── Goals / Tasks ──

export interface GoalsSummary {
  active_goals: number
  open_tasks: number
  overdue_tasks: number
  due_today_tasks: number
  recent_tasks: { id: string; title: string; status: string; created_at: string }[]
}

export interface GoalItem {
  id: string
  title: string
  description: string | null
  status: string
  source_journal_id: string | null
  recurrence: string
  recurrence_frequency: string | null
  due_at: string | null
  created_at: string
  tasks: TaskItem[]
}

export interface TaskItem {
  id: string
  title: string
  status: string
  goal_id: string | null
  source_journal_id: string | null
  recurrence: string
  recurrence_frequency: string | null
  due_at: string | null
  created_at: string
}

export async function apiGetGoalsSummary(): Promise<GoalsSummary> {
  return request<GoalsSummary>("/goals/summary")
}

export async function apiGetGoals(): Promise<{ goals: GoalItem[] }> {
  return request<{ goals: GoalItem[] }>("/goals")
}

export async function apiGetTasks(status?: string): Promise<{ tasks: TaskItem[] }> {
  const params = status ? `?status=${status}` : ""
  return request<{ tasks: TaskItem[] }>(`/goals/tasks${params}`)
}

export async function apiUpdateGoalStatus(goalId: string, status: string): Promise<GoalItem> {
  return request<GoalItem>(`/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  })
}

export async function apiUpdateGoal(goalId: string, data: {
  title?: string; description?: string; status?: string;
  recurrence?: string; recurrence_frequency?: string | null;
}): Promise<GoalItem> {
  return request<GoalItem>(`/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function apiUpdateTaskStatus(taskId: string, status: string): Promise<TaskItem> {
  return request<TaskItem>(`/goals/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  })
}

export async function apiUpdateTask(taskId: string, data: { title?: string; status?: string; due_at?: string | null }): Promise<TaskItem> {
  return request<TaskItem>(`/goals/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function apiDeleteGoal(goalId: string): Promise<void> {
  return request<void>(`/goals/${goalId}`, { method: "DELETE" })
}

export async function apiDeleteTask(taskId: string): Promise<void> {
  return request<void>(`/goals/tasks/${taskId}`, { method: "DELETE" })
}

export async function apiCreateGoal(data: {
  title: string; description?: string; due_at?: string;
  recurrence?: string; recurrence_frequency?: string;
}): Promise<GoalItem> {
  return request<GoalItem>("/goals/", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function apiCreateTask(data: {
  title: string; goal_id?: string; due_at?: string;
  recurrence?: string; recurrence_frequency?: string;
}): Promise<TaskItem> {
  return request<TaskItem>("/goals/tasks/", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

// ---- Agent CRUD ----

export async function apiCreateAgent(data: {
  name: string; purpose: string; tone: string; system_prompt?: string;
}): Promise<Agent> {
  return request<Agent>("/agents/", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function apiUpdateAgent(agentId: string, data: {
  name?: string; purpose?: string; tone?: string;
  system_prompt?: string; is_active?: boolean;
}): Promise<Agent> {
  return request<Agent>(`/agents/${agentId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function apiDeleteAgent(agentId: string): Promise<void> {
  return request<void>(`/agents/${agentId}`, { method: "DELETE" })
}

export async function apiToggleAgent(agentId: string): Promise<Agent> {
  return request<Agent>(`/agents/${agentId}/toggle`, { method: "PATCH" })
}

// ---- Export & Account ----

export async function apiExportJournals(): Promise<void> {
  const token = await getStoredToken()
  const res = await fetch(`${API_BASE}/journals/export`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!res.ok) throw new Error("Export failed")
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "MySaga_export.json"
  a.click()
  URL.revokeObjectURL(url)
}

export async function apiDeleteAccount(): Promise<void> {
  return request<void>("/auth/account", { method: "DELETE" })
}

// ---- Import ----

export interface ImportResult {
  imported: number
  skipped: number
  total: number
}

export async function apiImportJournals(data: unknown): Promise<ImportResult> {
  return request<ImportResult>("/journals/import", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

// ---- Insights ----

export interface InsightsData {
  period: string
  journal_count: number
  summary: string
  themes: string[]
  mood_trend: string
  accomplishments: string[]
  reflection_prompts: string[]
}

export async function apiGetInsights(period: "weekly" | "monthly"): Promise<InsightsData> {
  return request<InsightsData>(`/insights/${period}`)
}

// ---- Tags ----

export interface TagListResponse {
  tags: Tag[]
}

export async function apiGetTags(): Promise<TagListResponse> {
  return request<TagListResponse>("/journals/tags")
}

export async function apiGetJournalsByTag(tagId: string): Promise<JournalListResponse> {
  return request<JournalListResponse>(`/journals/by-tag/${tagId}`)
}
