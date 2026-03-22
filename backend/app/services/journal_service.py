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
    from app.models.goal import Goal
    from app.models.task import Task

    jid = journal.id

    # Delete goals and tasks sourced from this journal
    task_result = await db.execute(
        select(Task).where(Task.source_journal_id == jid)
    )
    for task in task_result.scalars().all():
        await db.delete(task)

    goal_result = await db.execute(
        select(Goal).where(Goal.source_journal_id == jid)
    )
    for goal in goal_result.scalars().all():
        await db.delete(goal)

    await db.delete(journal)
    await db.flush()


async def get_journal_dates_for_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
    tz_offset_minutes: int = 0,
) -> list[int]:
    """Return a list of day-of-month numbers that have at least one journal entry.
    tz_offset_minutes: offset from UTC in minutes (e.g. -420 for PDT)
    """
    from sqlalchemy import text
    # Convert UTC timestamp to user's local time by applying offset
    local_time = Journal.created_at + text(f"interval '{tz_offset_minutes} minutes'")
    q = (
        select(func.distinct(extract("day", local_time).cast(Integer)))
        .where(
            Journal.user_id == user_id,
            extract("year", local_time) == year,
            extract("month", local_time) == month,
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
    tz_offset_minutes: int = 0,
) -> list[Journal]:
    """Return all journals for a specific date in the user's local timezone."""
    from sqlalchemy import text
    local_time = Journal.created_at + text(f"interval '{tz_offset_minutes} minutes'")
    q = (
        select(Journal)
        .where(
            Journal.user_id == user_id,
            extract("year", local_time) == year,
            extract("month", local_time) == month,
            extract("day", local_time) == day,
        )
        .order_by(Journal.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())

