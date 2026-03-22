"""One-time migration: add agent_id column to journal_feedback table."""
import asyncio
from sqlalchemy import text
from app.db import engine


async def migrate():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE journal_feedback "
                "ADD COLUMN IF NOT EXISTS agent_id UUID "
                "REFERENCES agents(id) ON DELETE SET NULL"
            )
        )
        print("✓ agent_id column added to journal_feedback")


if __name__ == "__main__":
    asyncio.run(migrate())
