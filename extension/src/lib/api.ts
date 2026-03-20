import type { FeedbackListResponse, Journal, JournalListResponse, ProcessingStatus, TokenResponse, User } from "./types"

const API_BASE = "http://localhost:8000"

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const stored = await chrome.storage.local.get("token")
  const token = stored.token as string | undefined

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
  return request<number[]>(`/journals/dates?year=${year}&month=${month}`)
}

export async function apiGetJournalsByDate(year: number, month: number, day: number): Promise<JournalListResponse> {
  return request<JournalListResponse>(`/journals/by-date?year=${year}&month=${month}&day=${day}`)
}

// ---- Feedback (Phase 2) ----

export async function apiGetJournalFeedback(journalId: string): Promise<FeedbackListResponse> {
  return request<FeedbackListResponse>(`/journals/${journalId}/feedback`)
}

export async function apiGetJournalStatus(journalId: string): Promise<ProcessingStatus> {
  return request<ProcessingStatus>(`/journals/${journalId}/status`)
}
