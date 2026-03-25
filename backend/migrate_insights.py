import asyncio
from sqlalchemy import text
from app.db import engine

async def go():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS insight_cache (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    period VARCHAR(50) NOT NULL,
                    journal_hash VARCHAR(64) NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS ix_insight_cache_user_id ON insight_cache(user_id);
            """))
            print("Created insight_cache table")
        except Exception as e:
            print(f"Error: {e}")
    await engine.dispose()

asyncio.run(go())
