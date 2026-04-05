import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, auth, goals, insights, journals
from app.config import settings
from app.db import engine, Base, SessionLocal
from app.models import User, Journal, JournalFeedback, Agent, AgentThread, AgentMessage, Goal, Task, InsightCache, Tag, journal_tags  # noqa: F401 — register models

logger = logging.getLogger(__name__)

# Configure logging for app modules
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
logging.getLogger("app").setLevel(logging.DEBUG if settings.VERBOSE else logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience; use Alembic migrations in production)
    expected_tables = list(Base.metadata.tables.keys())
    logger.info("Expected tables from models: %s", expected_tables)
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("create_all completed successfully")
        except Exception as e:
            logger.error("create_all FAILED: %s (%s)", e, type(e).__name__)
            raise
        # Verify which tables actually exist in the database
        from sqlalchemy import inspect as sa_inspect
        actual_tables = await conn.run_sync(lambda sync_conn: sa_inspect(sync_conn).get_table_names())
        logger.info("Actual tables in database: %s", actual_tables)
        missing = set(expected_tables) - set(actual_tables)
        if missing:
            logger.error("MISSING TABLES after create_all: %s", missing)
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
    title="MySaga API",
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
