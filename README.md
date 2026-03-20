# Memory Journal — Chrome Extension

A memory-native journaling Chrome extension with a FastAPI backend and Plasmo-powered extension frontend.

## Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Docker Desktop** (for PostgreSQL)

---

## Database

```bash
cd backend
docker compose up -d        # Start PostgreSQL on port 5433
docker compose down -v      # Stop and wipe data (fresh start)
```

---

## Backend (FastAPI)

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

### Run Tests

```bash
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database — no Docker required.

---

## Extension (Plasmo + React)

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
