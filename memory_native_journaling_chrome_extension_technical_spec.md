# Technical Specification  
## Memory-Native Journaling Chrome Extension with EverMemOS

## 1. Overview

### 1.1 Product summary
Build a **Chrome extension-first journaling app** where users write journals directly inside the extension UI. Each completed journal entry is sent to your backend, which stores the raw entry, derives structured signals, and securely submits the entry to EverMemOS for memory extraction. EverMemOS provides persistent memory APIs for ingestion, retrieval, search, deletion, and metadata management, and all requests are authenticated with a bearer token that should never be exposed client-side.

After ingestion, the backend retrieves relevant prior memories and uses them plus app-owned structured data to generate personalized feedback from one or more configurable AI agents.

### 1.2 Core value proposition
The product is not just a journaling tool. It is a **memory-powered reflection system**:
- users journal inside the Chrome extension
- the system extracts durable memory over time
- AI agents respond with continuity across weeks and months
- the app helps with reflection, emotional support, and goal accountability

### 1.3 Hard requirements
- Frontend must be a **Chrome extension**
- EverMemOS API key must **never** be exposed in the extension
- A backend must sit between the extension and EverMemOS
- Multiple configurable AI agents must be supported
- Journal feedback must be grounded in previous journals and memories

## 2. Goals and non-goals

### 2.1 Goals
- Deliver a complete journaling experience fully accessible from a Chrome extension
- Persist long-term user memory via EverMemOS
- Generate personalized agent feedback using prior journals
- Support multiple role-based agents
- Support reminders, unfinished tasks, and goals
- Maintain privacy and role safety boundaries

### 2.2 Non-goals for MVP
- Full web app as primary UI
- Clinical therapy product
- Crisis intervention platform
- Fully autonomous agent action without user review
- Native mobile app

## 3. Product scope

## 3.1 User-facing surfaces in the Chrome extension

### A. Popup
Purpose: quick entry point
- open today’s journal
- continue draft
- view today’s reminders
- launch side panel or full-page extension view

### B. Side panel
Purpose: daily-use workspace
- short journaling
- select agent
- receive agent feedback
- ask follow-up questions
- view unresolved tasks/goals

### C. Full-page extension view
Purpose: deep workflows
- long-form journaling editor
- journal history
- agent management
- reminders and goals dashboard
- privacy/export/delete controls
- weekly and monthly summaries

This preserves your Chrome-plugin requirement while giving enough UI space for a real product.

## 4. High-level architecture

```text
Chrome Extension (MV3)
  ├─ Popup
  ├─ Side Panel
  ├─ Full-page Extension UI
  ├─ Background Service Worker
  └─ Local UI state/cache

        |
        | HTTPS + JWT/session
        v

Backend API
  ├─ Auth Service
  ├─ Journal Service
  ├─ Memory Orchestrator
  ├─ Agent Service
  ├─ Goal/Task Service
  ├─ Reminder Service
  ├─ Safety Layer
  └─ Job Queue / Workers

        |
        | Bearer auth
        v

EverMemOS Cloud
  ├─ POST /api/v0/memories
  ├─ GET /api/v0/memories/search
  ├─ GET /api/v0/status/request
  └─ Metadata APIs

        |
        v

LLM Provider
  └─ Generates agent feedback
```

## 5. Why a backend is mandatory

EverMemOS requires bearer-token authentication, so the extension should communicate only with your backend, and the backend should own EverMemOS access.

## 6. EverMemOS integration model

## 6.1 Relevant EverMemOS capabilities
EverMemOS supports:
- adding memories from messages/interactions
- retrieving memories with filters
- searching memories with keyword/vector/hybrid-style retrieval
- setting and updating conversation metadata
- checking async request processing status

## 6.2 Memory type model
EverMemOS defines four memory types:
- **Profile**: long-term identity and stable preferences
- **Episodic**: narrative summaries of past sessions/context
- **EventLog**: atomic facts/actions
- **Foresight**: future-oriented plans and intent

Important implementation detail:
- Profile memory retrieval/search behavior should be validated during implementation
- `foresight` and `event_log` should not be assumed to be first-class searchable for the MVP

Because of that, your product should use a **hybrid data model**:
- EverMemOS for long-term identity and narrative continuity
- your own database for goals, tasks, reminders, journal metadata, and agent configs

## 7. Recommended tech stack

### 7.1 Frontend
- Chrome Extension Manifest V3
- React + TypeScript
- Vite or Plasmo
- Zustand or Redux Toolkit for state
- Tailwind CSS
- IndexedDB for local drafts/cache

### 7.2 Backend
- FastAPI or NestJS
- PostgreSQL
- Redis
- Celery / RQ / BullMQ for async jobs
- OpenAI or equivalent LLM provider
- S3-compatible object storage for exports/backups if needed

### 7.3 Observability
- structured logs
- Sentry
- OpenTelemetry
- metrics dashboard for ingestion latency and agent latency

## 8. Chrome extension architecture

## 8.1 Manifest V3 components

### Required components
- `action` popup
- `side_panel`
- extension page route
- `background.service_worker`
- optional `alarms`
- optional `notifications`
- secure storage for session token only, never EverMemOS key

### Suggested file structure
```text
extension/
  manifest.json
  src/
    popup/
      PopupApp.tsx
    sidepanel/
      SidePanelApp.tsx
    pages/
      home/
      journal/
      history/
      agents/
      settings/
      insights/
    background/
      serviceWorker.ts
    content/
    lib/
      api.ts
      auth.ts
      storage.ts
      types.ts
    components/
```

## 8.2 Extension responsibilities
The extension is responsible for:
- user authentication session handling
- rendering journaling UI
- saving local drafts
- calling backend APIs
- showing agent feedback
- showing reminders
- managing agent settings UI

The extension is not responsible for:
- direct EverMemOS calls
- secret storage
- prompt orchestration
- long-running polling logic beyond light UX polling
- deep analytics computation

## 9. Backend architecture

## 9.1 Services

### Auth service
- sign-in / token refresh
- extension session validation
- user identity mapping

### Journal service
- create/update/fetch journals
- store drafts and finalized entries
- store journal metadata

### Memory orchestrator
- map journal submission to EverMemOS ingestion
- poll request status
- run memory retrieval
- normalize retrieved memory

### Agent service
- build context packages
- run prompts against LLM
- store outputs
- support follow-up conversations per agent

### Goal/task service
- extract goals/tasks from journals
- track completion state
- power secretary/reminder agent

### Reminder service
- daily reminders
- weekly reviews
- Chrome notification scheduling hooks

### Safety service
- detect crisis/self-harm/high-risk content
- switch to safe-response templates
- enforce role boundaries

## 9.2 Suggested backend modules
```text
backend/
  app/
    api/
      auth.py
      journals.py
      agents.py
      reminders.py
      insights.py
    services/
      evermemos.py
      journals.py
      agents.py
      prompts.py
      goals.py
      reminders.py
      safety.py
    workers/
      process_journal.py
      generate_feedback.py
      weekly_digest.py
    models/
    schemas/
    db/
```

## 10. Data model

## 10.1 Core entities

### users
```text
id
email
name
created_at
updated_at
settings_json
```

### journals
```text
id
user_id
title
raw_text
markdown_text
status            // draft | submitted | processed | failed
created_at
updated_at
submitted_at
word_count
mood_label
source_surface    // popup | sidepanel | fullpage
evermemos_request_id
evermemos_status
```

### journal_artifacts
```text
id
journal_id
summary
emotion_labels_json
themes_json
people_json
goals_json
tasks_json
coping_strategies_json
risk_flags_json
created_at
```

### agents
```text
id
user_id
name
role
purpose
tone
memory_policy_json
guardrails_json
output_schema_json
system_prompt
is_builtin
is_active
created_at
updated_at
```

### journal_feedback
```text
id
journal_id
agent_id
retrieved_memory_snapshot_json
structured_context_snapshot_json
response_text
response_json
model_name
created_at
```

### goals
```text
id
user_id
title
description
status            // active | paused | completed | abandoned
source_journal_id
due_at
priority
created_at
updated_at
```

### tasks
```text
id
user_id
goal_id
title
status            // open | completed | dismissed
source_journal_id
due_at
last_reminded_at
created_at
updated_at
```

### reminders
```text
id
user_id
agent_id
type              // daily | weekly | goal_followup
schedule_json
is_enabled
last_sent_at
created_at
updated_at
```

### agent_threads
```text
id
user_id
agent_id
journal_id_nullable
created_at
updated_at
```

### agent_messages
```text
id
thread_id
role              // user | assistant | system
content
created_at
```

## 11. Agent model

## 11.1 Agent definition
Each agent should be a bounded configuration, not an unconstrained persona.

```json
{
  "name": "Reflection Coach",
  "role": "reflection_coach",
  "purpose": "Help the user notice patterns and make sense of entries over time",
  "tone": "warm, curious, nonjudgmental",
  "memory_policy": {
    "use_episodic": true,
    "use_profile": true,
    "max_memories": 8,
    "time_window_days": 90
  },
  "guardrails": {
    "no_diagnosis": true,
    "no_dependency_language": true,
    "crisis_safe_mode": true
  },
  "output_schema": {
    "sections": [
      "today_summary",
      "pattern_connection",
      "supportive_observation",
      "next_step",
      "reflection_question"
    ]
  }
}
```

## 11.2 Built-in agents for MVP
- Reflection Coach
- Goal Secretary
- Supportive Friend
- Inner Caregiver

## 11.3 Role boundaries
Do not frame agents as licensed therapists or literal parents. Safer framing:
- “Inner Caregiver” instead of “Parent”
- “Emotional Processing Guide” instead of “Talk Therapist”

## 12. Journal submission flow

## 12.1 End-to-end sequence

```text
User writes journal in extension
  -> Extension POST /journals
  -> Backend stores journal
  -> Backend derives structured artifacts
  -> Backend calls EverMemOS POST /api/v0/memories
  -> EverMemOS returns request_id with status=queued
  -> Backend polls GET /api/v0/status/request?request_id=...
  -> Backend searches memories via GET /api/v0/memories/search
  -> Backend assembles context package
  -> Backend calls LLM for selected agent
  -> Backend stores feedback
  -> Extension fetches and renders feedback
```

## 12.2 Recommended EverMemOS ingestion payload
Example backend request body:

```json
{
  "message_id": "journal_01HVXYZ",
  "create_time": "2026-03-19T22:10:00-07:00",
  "sender": "user_123",
  "sender_name": "Alice",
  "role": "user",
  "content": "Today I felt anxious about work...",
  "group_id": "user_123_journal",
  "group_name": "Alice Journal Stream",
  "flush": true
}
```

## 13. Memory retrieval strategy

## 13.1 Retrieval policy
For feedback generation:
- query EverMemOS with the current journal summary or full entry
- request `episodic_memory` by default
- optionally include `profile` if available
- constrain by time window when appropriate
- store the retrieved snapshot used for generation

## 13.2 Recommended retrieval config by agent

### Reflection Coach
- query: journal summary + top emotional themes
- memory_types: episodic + profile
- method: hybrid or rrf
- time window: 30 to 90 days

### Goal Secretary
- EverMemOS: episodic memories mentioning intentions
- App DB: tasks/goals/reminders as primary truth
- time window: 14 to 30 days

### Supportive Friend
- query: emotional state + current concerns
- memory_types: episodic + profile
- method: hybrid
- time window: 60 days

### Inner Caregiver
- query: distress language + self-worth themes
- memory_types: episodic + profile
- method: hybrid
- stricter safety filters

## 14. Backend API spec

## 14.1 Auth
### POST /auth/login
Start auth flow or exchange token

### POST /auth/refresh
Refresh session

### GET /auth/me
Get current user

## 14.2 Journals
### POST /journals
Create draft or submit final entry

Request:
```json
{
  "title": "March 19 check-in",
  "content": "I felt exhausted today...",
  "submit": true,
  "source_surface": "sidepanel",
  "selected_agent_id": "agent_reflection_default"
}
```

Response:
```json
{
  "journal_id": "jr_123",
  "status": "submitted",
  "processing_status": "queued"
}
```

### GET /journals
List journals

### GET /journals/{id}
Get journal detail and feedback

### PATCH /journals/{id}
Update draft

### DELETE /journals/{id}
Delete journal

## 14.3 Agents
### GET /agents
List agents

### POST /agents
Create custom agent

### PATCH /agents/{id}
Update agent

### DELETE /agents/{id}
Delete agent

### POST /agents/{id}/respond
Generate agent response for a given journal or freeform chat input

## 14.4 Goals and tasks
### GET /goals
### POST /goals
### PATCH /goals/{id}
### GET /tasks
### PATCH /tasks/{id}

## 14.5 Reminders
### GET /reminders/today
### POST /reminders
### PATCH /reminders/{id}
### DELETE /reminders/{id}

## 14.6 Insights
### GET /insights/weekly
### GET /insights/monthly
### GET /insights/themes

## 15. Background job design

## 15.1 Job types
### process_journal_submission
- derive artifacts
- send to EverMemOS
- poll request status
- trigger feedback generation

### generate_agent_feedback
- retrieve memories
- build prompt
- call LLM
- persist response

### refresh_secretary_digest
- scan open tasks/goals
- generate reminder summary

### weekly_reflection_digest
- summarize week
- identify patterns
- optionally notify extension

## 15.2 Polling behavior
Because add-memories returns a queued request and request status is queried separately, use async workers rather than blocking extension requests. Accept submission immediately, then let the extension poll your backend for processing progress.

Recommended polling:
- backend polls EverMemOS every 1.5 to 3 seconds
- max wait per journal processing job: 30 to 60 seconds
- if still pending, mark as deferred and continue asynchronously
- extension shows “memory processing in progress”

## 16. Prompt orchestration

## 16.1 Context package
Each prompt should be assembled from:
- current journal text
- current journal summary
- retrieved EverMemOS memories
- app-owned structured artifacts
- active goals/tasks
- agent config
- safety status

## 16.2 Example system prompt skeleton
```text
You are the user's Reflection Coach.
Your role is to help the user reflect on their journal with warmth and clarity.

Use the user's previous memories only to provide continuity.
Do not diagnose.
Do not exaggerate certainty.
If the user appears in crisis, switch to safe supportive guidance.

Return:
1. Today summary
2. Pattern connection
3. Supportive observation
4. Practical next step
5. Reflection question
```

## 17. Safety specification

## 17.1 Safety principles
- no clinical diagnosis
- no literal parental replacement framing
- no manipulative dependence language
- no guaranteed emotional claims
- no trauma-treatment claims

## 17.2 Safety modes
### Normal mode
Standard role behavior

### Sensitive mode
Activated for elevated distress
- gentler output
- avoid strong interpretations
- recommend grounding

### Crisis mode
Activated for self-harm or imminent-risk signals
- no normal persona response
- show supportive crisis-safe template
- provide emergency/help-seeking guidance based on locale if available

## 17.3 Safety filters
Run before generation:
- self-harm classifier
- abuse/immediate danger cues
- delusion/paranoia-sensitive cues
- severe dissociation/manic-language heuristics

## 18. Privacy and security

## 18.1 Security requirements
- EverMemOS API key only on backend
- HTTPS only
- JWT or secure session token between extension and backend
- encrypted secrets at rest
- least-privilege DB roles
- audit logs for memory deletion/export events

## 18.2 User privacy controls
- export all journals
- delete journal
- delete memory sync history
- disable specific agent memory access
- opt out of certain artifact extraction types
- “do not use this entry for agent coaching” toggle

## 18.3 Data retention
Recommended:
- raw journals retained until user deletes
- derived artifacts retained until user deletes
- feedback snapshots retained for explainability
- local drafts stored in IndexedDB and purgeable

## 19. Extension UX flows

## 19.1 New journal flow
- user opens popup
- clicks “New Journal”
- extension opens side panel or full-page view
- user writes
- selects agent
- clicks Submit
- UI shows processing states:
  - saving
  - extracting memory
  - generating feedback
  - ready

## 19.2 Follow-up chat flow
- after feedback, user asks follow-up
- backend reuses journal context + retrieved memories + thread history
- response appended to agent thread

## 19.3 Secretary reminder flow
- background worker computes unresolved goals/tasks
- backend returns reminder summary
- extension popup shows “Today’s reminders”
- optional Chrome notification launches side panel

## 20. MVP definition

## 20.1 MVP v1
- Chrome extension popup, side panel, full-page route
- auth
- journal editor
- submit journal
- backend EverMemOS ingestion
- async request-status polling
- memory retrieval
- one built-in Reflection Coach
- history page
- feedback page

## 20.2 MVP v1.5
- Goal Secretary
- tasks/goals extraction
- reminders
- custom agents
- follow-up chat

## 20.3 v2
- weekly/monthly insights
- emotion timeline
- multiple simultaneous agent responses
- voice journaling
- richer proactive workflows

## 21. Recommended implementation order

### Phase 1
- extension shell
- auth
- full-page journal editor
- backend journal create/read
- local drafts

### Phase 2
- EverMemOS integration
- journal submission worker
- request-status polling
- feedback rendering

### Phase 3
- reflection agent
- follow-up chat
- journal history

### Phase 4
- goals/tasks extraction
- secretary agent
- reminders
- popup summary widgets

### Phase 5
- custom agent builder
- insights
- export/delete/privacy controls

## 22. Risks and mitigations

### Risk: extension UI feels cramped
Mitigation:
- use side panel and full-page route for core workflows

### Risk: EverMemOS async extraction adds latency
Mitigation:
- async workers
- optimistic UI states
- partial-response fallback before memory completes

### Risk: goals/tasks retrieval weak if relying only on EverMemOS
Mitigation:
- keep goals/tasks as first-class DB entities

### Risk: emotionally loaded agent roles create safety issues
Mitigation:
- bounded roles
- renamed caregiver/processing roles
- safety mode switching

## 23. Open engineering decisions

You should decide early:
- FastAPI vs NestJS
- Plasmo vs raw MV3 + Vite
- Postgres JSONB-heavy schema vs more normalized model
- whether to support extension-only auth or external OAuth login page
- whether follow-up chat is per journal or per agent-global thread

## 24. Final recommendation

Build the product around one primary loop:

**write journal in Chrome extension → submit to backend → extract memory in EverMemOS → retrieve relevant prior context → generate feedback from a bounded agent**

Then add the second loop:

**extract goals/tasks from journals → secretary agent reminds user about unfinished intentions**

That gives you a technically realistic MVP with a Chrome extension frontend, secure backend processing layer, and a hybrid data model that combines long-term memory with app-owned structured entities.

