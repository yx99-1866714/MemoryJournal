import asyncio
from sqlalchemy import text
from app.db import engine

async def go():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE agent_threads ADD COLUMN last_proactive_checkin_at TIMESTAMP WITH TIME ZONE"))
            print("Added last_proactive_checkin_at")
        except Exception as e:
            print(f"col1: {e}")
        try:
            await conn.execute(text("ALTER TABLE agent_threads ADD COLUMN last_read_at TIMESTAMP WITH TIME ZONE"))
            print("Added last_read_at")
        except Exception as e:
            print(f"col2: {e}")
    await engine.dispose()

asyncio.run(go())
