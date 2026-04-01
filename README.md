# MySaga
![alt text](image-1.png)
A memory-powered AI journaling Chrome extension with persistent AI companions. Write daily journal entries, and a team of AI agents — powered by your accumulated memories — will help you reflect, set goals, track habits, and manage your emotional wellbeing.

Video Demo Link: https://youtu.be/4P9wEJxaH8Q

Want to try it? Download from "Releases" section to the right

---

## What Is MySaga?

MySaga is a Chrome extension (side panel + full-page dashboard) backed by a FastAPI server. It connects to [EverMemOS](https://docs.evermind.ai/cloud/overview) for long-term memory storage and uses LLMs (via OpenRouter) to power a suite of AI companions that grow smarter over time as they learn from your journal entries.

Unlike typical journaling apps, MySaga doesn't just store text — it **processes** every entry through multiple AI agents, stores insights as searchable memories, and uses that growing context to provide increasingly personalized support.

---

## Key Features

### 📓 Journaling
![alt text](image-2.png)
- **Quick Entry** via the Chrome side panel — write journal entries without leaving your current tab
- **Full Dashboard** with a calendar view, journal history, and rich editing
- **Auto-titling** — AI generates concise titles for each entry
- **Re-processing** — edit a journal and re-submit it; AI agents re-analyze while preserving chat history

### 🤖 AI Companions
![alt text](image-3.png)
Four built-in AI agents, each with a distinct personality and role:

| Agent | Role | What It Does |
|-------|------|-------------|
| 🪞 **Reflection Coach** | `reflection_coach` | Helps you identify patterns, reframe perspectives, and gain self-awareness |
| 📋 **Goal Secretary** | `goal_secretary` | Manages goals and tasks through conversation — can **create, edit, and delete** goals/tasks directly via chat |
| 💛 **Supportive Friend** | `supportive_friend` | Provides emotional support, validates feelings, and offers encouragement |
| 🤗 **Inner Caregiver** | `inner_caregiver` | Promotes self-compassion and suggests self-care actions |

You can also **create custom agents** with your own name, purpose, tone, and system prompt.

### 🎯 Goals & Task Management
![alt text](image-4.png)

- **AI-powered goal creation** — tell the Goal Secretary "help me plan a workout routine" and it creates goals + tasks
- **One-time tasks** with deadline dates
- **Recurring tasks** (daily/weekly) that auto-reset:
  - Daily tasks reset to incomplete at the start of each day
  - Weekly tasks reset to incomplete every Monday
- **Visual dashboard** with progress tracking, overdue alerts, and task completion

### 💬 Proactive Check-ins
![alt text](image-5.png)
AI agents **proactively reach out** to you based on your emotional state:
- **Critical urgency** (e.g., breakup, crisis) → check-ins every hour
- **Elevated urgency** (e.g., stress, anxiety) → check-ins every 24 hours
- **Normal** → check-ins every 7 days

The check-in scheduler runs in the background and generates contextually-aware messages based on recent journals, chat history, and goals.

### 📊 Insights & Analytics
![alt text](image-6.png)
- Weekly pattern analysis and emotional trend tracking
- Memory-powered insights that surface recurring themes
- Goal progress summaries

### 🔴 Unread Message Indicators
- Red dot badges on agent cards, navbar, dashboard buttons, side panel, and browser popup
- Badge clears automatically when you open a chat
- Browser action badge shows total unread count

### 🧠 Memory-Powered Context
- Every journal entry is processed and stored as searchable memories via EverMemOS
- AI agents retrieve relevant memories when responding, enabling long-term continuity
- Agents reference past conversations and journal entries for deeply personalized responses

---

## Architecture

```
┌─────────────────────────────────┐
│   Chrome Extension (Plasmo)     │
│  ┌───────────┐ ┌──────────────┐ │
│  │ Side Panel│ │  Full Page   │ │
│  │ (Journal  │ │  Dashboard   │ │
│  │  + Chat)  │ │ (Journals,   │ │
│  │           │ │  Goals, Chat)│ │
│  └───────────┘ └──────────────┘ │
│  ┌───────────┐ ┌──────────────┐ │
│  │  Popup    │ │  Background  │ │
│  │           │ │  (Badge sync)│ │
│  └───────────┘ └──────────────┘ │
└─────────────┬───────────────────┘
              │ REST API
┌─────────────▼───────────────────┐
│   FastAPI Backend               │
│  ┌──────────────────────────┐   │
│  │ API Routes               │   │
│  │ auth, journals, agents,  │   │
│  │ goals, insights          │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │ Services                 │   │
│  │ LLM, journal processing, │   │
│  │ check-in scheduler,      │   │
│  │ goal actions, recurring  │   │
│  │ tasks, EverMemOS client   │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │ PostgreSQL + SQLAlchemy  │   │
│  └──────────────────────────┘   │
└─────────────┬───────────────────┘
              │
   ┌──────────▼──────────┐
   │  External Services   │
   │  • OpenRouter (LLM)  │
   │  • EverMemOS (Memory) │
   └──────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Plasmo, React, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy (async), Pydantic |
| **Database** | PostgreSQL (via Docker) |
| **LLM** | OpenRouter API (configurable model, default: Grok) |
| **Memory** | EverMemOS API |
| **Auth** | JWT-based authentication |

---

## Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Docker Desktop** (for PostgreSQL)

---

## Getting Started

### Database

```bash
cd backend
docker compose up -d        # Start PostgreSQL on port 5433
docker compose down -v      # Stop and wipe data (fresh start)
```

### Backend (FastAPI)

```bash
cd backend

# First-time setup
python -m venv venv
.\venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Run the dev server
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

API docs: **http://localhost:8000/docs**

#### Run Tests

```bash
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database — no Docker required.

#### Environment Variables

Create `backend/.env` with:

```env
DATABASE_URL=postgresql+asyncpg://memoryjournal:memoryjournal_dev@localhost:5433/memoryjournal
JWT_SECRET=your-secret-key

# EverMemOS + LLM (optional, features degrade gracefully)
EVERMEMOS_API_KEY=your-evermemos-key
EVERMEMOS_API_URL=https://api.evermemos.com
OPENROUTER_API_KEY=your-openrouter-key
LLM_MODEL=x-ai/grok-4-fast
```

### Extension (Plasmo + React)

```bash
cd extension

# First-time setup
npm install

# Dev mode (hot reload)
npm run dev

# Production build
npm run build
```

Then load the extension in Chrome:
1. Go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select `extension/build/chrome-mv3-dev` (dev) or `extension/build/chrome-mv3-prod` (prod)

---

## Project Structure

```
MySaga/
├── backend/
│   ├── app/
│   │   ├── api/            # REST endpoints (auth, journals, agents, goals, insights)
│   │   ├── models/         # SQLAlchemy models (User, Journal, Agent, Goal, Task, etc.)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (LLM, journal processing, scheduling)
│   │   ├── config.py       # Environment config
│   │   ├── db.py           # Database engine & session
│   │   └── main.py         # FastAPI app entry point
│   ├── tests/              # Pytest test suite
│   ├── docker-compose.yml  # PostgreSQL container
│   └── requirements.txt
├── extension/
│   ├── src/
│   │   ├── components/     # React components (ChatWindow, GoalsDashboard, etc.)
│   │   ├── lib/            # API client, types, constants
│   │   ├── store/          # Zustand state management
│   │   ├── tabs/           # Full-page dashboard (index.tsx)
│   │   └── background.ts   # Service worker (badge sync)
│   ├── sidepanel.tsx       # Side panel entry point
│   ├── popup.tsx           # Browser popup
│   └── package.json
└── README.md
```
