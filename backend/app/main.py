from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, journals
from app.db import engine, Base
from app.models import User, Journal  # noqa: F401 — register models with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience; use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
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
        "chrome-extension://*",
        "http://localhost:3000",  # dev convenience
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(journals.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
