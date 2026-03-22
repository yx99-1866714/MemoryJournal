"""
Migration: Add recurrence columns to goals and tasks tables.
Run: python -m app.migrations.add_recurrence_columns
"""
import asyncio
from sqlalchemy import text
from app.db import engine


async def migrate():
    async with engine.begin() as conn:
        # Add recurrence columns to goals table
        await conn.execute(text(
            "ALTER TABLE goals ADD COLUMN IF NOT EXISTS recurrence VARCHAR(20) NOT NULL DEFAULT 'one_time'"
        ))
        await conn.execute(text(
            "ALTER TABLE goals ADD COLUMN IF NOT EXISTS recurrence_frequency VARCHAR(20)"
        ))

        # Add recurrence columns to tasks table
        await conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recurrence VARCHAR(20) NOT NULL DEFAULT 'one_time'"
        ))
        await conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recurrence_frequency VARCHAR(20)"
        ))

        print("✅ Added recurrence columns to 'goals' and 'tasks' tables.")


if __name__ == "__main__":
    asyncio.run(migrate())
