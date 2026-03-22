"""
Insights API — generate weekly/monthly journal summaries using the LLM.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.config import settings
from app.db import get_db
from app.models.journal import Journal

router = APIRouter(prefix="/insights", tags=["insights"])


async def _gather_journals(
    db: AsyncSession, user_id: uuid.UUID, days: int,
) -> list[dict]:
    """Fetch journals from the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(Journal)
        .where(Journal.user_id == user_id, Journal.created_at >= cutoff)
        .order_by(Journal.created_at.desc())
    )
    journals = result.scalars().all()
    return [
        {
            "title": j.title or "Untitled",
            "content": j.raw_text[:500] if j.raw_text else "",
            "mood": j.mood_label,
            "date": j.created_at.isoformat() if j.created_at else None,
        }
        for j in journals
    ]


async def _generate_insights(journals: list[dict], period: str) -> dict:
    """Call LLM to generate insights from journal summaries."""
    if not journals:
        return {
            "period": period,
            "journal_count": 0,
            "summary": "No journal entries found for this period.",
            "themes": [],
            "mood_trend": "Not enough data",
            "accomplishments": [],
            "reflection_prompts": [],
        }

    # Build context from journals
    entries_text = "\n\n".join(
        f"[{j['date'][:10] if j['date'] else 'Unknown'}] {j['title']}\n{j['content']}"
        for j in journals[:20]  # Limit to 20 entries to stay within token limits
    )

    if not settings.OPENROUTER_API_KEY:
        # Fallback for dev without API key
        return {
            "period": period,
            "journal_count": len(journals),
            "summary": f"You wrote {len(journals)} journal entries this {period}.",
            "themes": ["Reflection", "Growth"],
            "mood_trend": "Varied",
            "accomplishments": ["Consistent journaling"],
            "reflection_prompts": ["What patterns do you notice in your writing?"],
        }

    import httpx

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    messages = [
        {
            "role": "system",
            "content": (
                f"Analyze these {period} journal entries and provide insights. "
                "Return a JSON object with these fields:\n"
                '- "summary": A 2-3 sentence summary of the period\n'
                '- "themes": Array of 3-5 key themes/topics\n'
                '- "mood_trend": A brief description of emotional patterns\n'
                '- "accomplishments": Array of 2-4 notable achievements or progress\n'
                '- "reflection_prompts": Array of 2-3 thoughtful questions for further reflection\n'
                "Return ONLY valid JSON, no markdown formatting."
            ),
        },
        {"role": "user", "content": entries_text},
    ]

    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://memoryjournal.app",
        "X-Title": "Memory Journal",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        import json
        raw = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
        parsed["period"] = period
        parsed["journal_count"] = len(journals)
        return parsed
    except Exception:
        return {
            "period": period,
            "journal_count": len(journals),
            "summary": f"You wrote {len(journals)} journal entries this {period}.",
            "themes": [],
            "mood_trend": "Unable to analyze",
            "accomplishments": [],
            "reflection_prompts": [],
        }


@router.get("/weekly")
async def weekly_insights(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate insights from the past 7 days of journal entries."""
    journals = await _gather_journals(db, uuid.UUID(user_id), days=7)
    return await _generate_insights(journals, "weekly")


@router.get("/monthly")
async def monthly_insights(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate insights from the past 30 days of journal entries."""
    journals = await _gather_journals(db, uuid.UUID(user_id), days=30)
    return await _generate_insights(journals, "monthly")
