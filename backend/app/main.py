import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, auth, goals, insights, journals
from app.config import settings
from app.db import engine, Base, SessionLocal
from app.models import User, Journal, Agent, AgentThread, AgentMessage  # noqa: F401 — register models

# Configure logging for app modules
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
logging.getLogger("app").setLevel(logging.DEBUG if settings.VERBOSE else logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience; use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed built-in agents
    from app.services.agent_service import seed_builtin_agents
    async with SessionLocal() as db:
        await seed_builtin_agents(db)

    # Start proactive check-in scheduler as background task
    import asyncio
    from app.services.checkin_scheduler import start_scheduler_loop
    scheduler_task = asyncio.create_task(start_scheduler_loop())

    yield

    scheduler_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="MemoryJournal API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Chrome extension origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # dev convenience
        "http://localhost:5173",
    ],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(journals.router)
app.include_router(agents.router)
app.include_router(goals.router)
app.include_router(insights.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
