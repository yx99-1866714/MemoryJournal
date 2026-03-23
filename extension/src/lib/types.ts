// ---- User ----

export interface User {
  id: string
  email: string
  name: string
}

export interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
}

// ---- Journal ----

export type JournalStatus = "draft" | "submitted" | "processed" | "failed"
export type SourceSurface = "popup" | "sidepanel" | "fullpage"

export interface Tag {
  id: string
  name: string
  journal_count?: number
}

export interface Journal {
  id: string
  user_id: string
  title: string | null
  raw_text: string
  status: JournalStatus
  word_count: number | null
  mood_label: string | null
  source_surface: SourceSurface | null
  created_at: string
  updated_at: string
  submitted_at: string | null
  tags: Tag[]
}

export interface JournalDraft {
  id: string // local UUID
  title: string
  content: string
  mood_label: string | null
  source_surface: SourceSurface
  updated_at: number // timestamp
}

export interface Agent {
  id: string
  name: string
  role: string
  purpose: string
  tone: string
  is_builtin: boolean
  is_active: boolean
  unread_count: number
}

export interface AgentListResponse {
  agents: Agent[]
}

export interface AgentMessage {
  id: string
  thread_id: string
  role: string
  content: string
  created_at: string
}

export interface AgentThread {
  id: string
  agent_id: string
  journal_id: string | null
  messages: AgentMessage[]
  created_at: string
}

export interface AgentRespondRequest {
  message: string
  journal_id?: string
  tz_offset_minutes?: number
}

// ---- API ----

export interface JournalListResponse {
  journals: Journal[]
  total: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ---- Feedback (Phase 2) ----

export interface Feedback {
  id: string
  journal_id: string
  agent_role: string
  response_text: string
  response_json: {
    today_summary?: string
    pattern_connection?: string
    supportive_observation?: string
    next_step?: string
    reflection_question?: string
  } | null
  model_name: string | null
  created_at: string
}

export interface FeedbackListResponse {
  feedback: Feedback[]
}

export interface ProcessingStatus {
  journal_id: string
  status: string
  evermemos_status: string | null
  has_feedback: boolean
}
