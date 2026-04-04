"""
Migration script to create the tags, journal_tags, and insight_cache tables.

Run this on Render's PostgreSQL if they weren't auto-created:
  python migrate_tags.py
"""
import asyncio
from sqlalchemy import text
from app.db import engine


async def go():
    async with engine.begin() as conn:
        # Create tags table
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tags (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS ix_tags_user_id ON tags(user_id);
            """))
            print("✓ Created 'tags' table")
        except Exception as e:
            print(f"✗ Error creating 'tags': {e}")

        # Create journal_tags association table
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS journal_tags (
                    journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
                    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (journal_id, tag_id)
                );
            """))
            print("✓ Created 'journal_tags' table")
        except Exception as e:
            print(f"✗ Error creating 'journal_tags': {e}")

        # Create insight_cache table
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
            print("✓ Created 'insight_cache' table")
        except Exception as e:
            print(f"✗ Error creating 'insight_cache': {e}")

    await engine.dispose()
    print("\nDone! All tables checked/created.")


if __name__ == "__main__":
    asyncio.run(go())
