"""
Migration: Create goals and tasks tables for Phase 4.
Run: python -m app.migrations.create_goals_tasks
"""
import asyncio
from app.db import engine, Base
from app.models import Goal, Task  # noqa: F401 — ensure models are registered


async def migrate():
    async with engine.begin() as conn:
        # Create only the new tables
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[Goal.__table__, Task.__table__],
        )
        print("✅ Created 'goals' and 'tasks' tables.")


if __name__ == "__main__":
    asyncio.run(migrate())
