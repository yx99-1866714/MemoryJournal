import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, extract, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import Journal


async def create_journal(
    db: AsyncSession,
    user_id: uuid.UUID,
    content: str,
    title: str | None = None,
    submit: bool = False,
    source_surface: str | None = None,
    mood_label: str | None = None,
) -> Journal:
    journal = Journal(
        user_id=user_id,
        title=title,
        raw_text=content,
        status="submitted" if submit else "draft",
        word_count=len(content.split()),
        mood_label=mood_label,
        source_surface=source_surface,
        submitted_at=datetime.now(timezone.utc) if submit else None,
    )
    db.add(journal)
    await db.flush()
    await db.refresh(journal)
    return journal


async def get_journals(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Journal], int]:
    # Count
    count_q = select(func.count()).select_from(Journal).where(Journal.user_id == user_id)
    total = (await db.execute(count_q)).scalar_one()

    # Fetch
    q = (
        select(Journal)
        .where(Journal.user_id == user_id)
        .order_by(Journal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def get_journal(
    db: AsyncSession, journal_id: uuid.UUID, user_id: uuid.UUID
) -> Journal | None:
    result = await db.execute(
        select(Journal).where(Journal.id == journal_id, Journal.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_journal(
    db: AsyncSession,
    journal: Journal,
    content: str | None = None,
    title: str | None = None,
    submit: bool | None = None,
    mood_label: str | None = None,
) -> Journal:
    if title is not None:
        journal.title = title
    if content is not None:
        journal.raw_text = content
        journal.word_count = len(content.split())
    if mood_label is not None:
        journal.mood_label = mood_label
    if submit:
        journal.status = "submitted"
        journal.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(journal)
    return journal


async def delete_journal(db: AsyncSession, journal: Journal) -> None:
    await db.delete(journal)
    await db.flush()


async def get_journal_dates_for_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> list[int]:
    """Return a list of day-of-month numbers that have at least one journal entry."""
    q = (
        select(func.distinct(extract("day", Journal.created_at).cast(Integer)))
        .where(
            Journal.user_id == user_id,
            extract("year", Journal.created_at) == year,
            extract("month", Journal.created_at) == month,
        )
    )
    result = await db.execute(q)
    return sorted([int(row[0]) for row in result.all()])


async def get_journals_by_date(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
    day: int,
) -> list[Journal]:
    """Return all journals for a specific date."""
    q = (
        select(Journal)
        .where(
            Journal.user_id == user_id,
            extract("year", Journal.created_at) == year,
            extract("month", Journal.created_at) == month,
            extract("day", Journal.created_at) == day,
        )
        .order_by(Journal.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())

