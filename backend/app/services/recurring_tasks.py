"""
Recurring task generation — creates periodic tasks from recurring goals.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from calendar import monthrange

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.task import Task

logger = logging.getLogger(__name__)


def _period_bounds(frequency: str, now: datetime) -> tuple[datetime, datetime]:
    """
    Return (period_start, period_end) for the given frequency at noon UTC,
    so timezone offsets up to ±12h never shift the calendar day.
    """
    if frequency == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    elif frequency == "weekly":
        # Monday = 0 … Sunday = 6
        monday = now - timedelta(days=now.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + timedelta(days=6)
        end = sunday.replace(hour=23, minute=59, second=59, microsecond=0)
    elif frequency == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = monthrange(now.year, now.month)[1]
        end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
    elif frequency == "yearly":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
    else:
        raise ValueError(f"Unknown frequency: {frequency}")
    return start, end


async def generate_recurring_tasks(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Check all active recurring goals for the user and create tasks
    for the current period if one doesn't already exist.

    Returns the number of tasks created.
    """
    now = datetime.now(timezone.utc)

    # Fetch active recurring goals
    result = await db.execute(
        select(Goal).where(
            Goal.user_id == user_id,
            Goal.status == "active",
            Goal.recurrence == "recurring",
            Goal.recurrence_frequency.isnot(None),
        )
    )
    goals = list(result.scalars().all())

    if not goals:
        return 0

    created_count = 0

    for goal in goals:
        freq = goal.recurrence_frequency
        if freq not in ("daily", "weekly", "monthly", "yearly"):
            continue

        period_start, period_end = _period_bounds(freq, now)

        # Check if a task already exists for this goal in the current period
        existing = await db.execute(
            select(Task.id).where(
                Task.goal_id == goal.id,
                Task.user_id == user_id,
                Task.due_at >= period_start,
                Task.due_at <= period_end,
            )
        )
        if existing.first() is not None:
            continue  # task already exists for this period

        # Create a new task with deadline at noon UTC on the last day of the period
        deadline = period_end.replace(hour=12, minute=0, second=0, microsecond=0)

        new_task = Task(
            user_id=user_id,
            goal_id=goal.id,
            title=goal.title,
            status="open",
            due_at=deadline,
            recurrence="one_time",  # individual task is one-time
            recurrence_frequency=None,
        )
        db.add(new_task)
        created_count += 1
        logger.info(
            "Created recurring task for goal %s (%s), period %s–%s",
            goal.id, freq,
            period_start.strftime("%Y-%m-%d"),
            period_end.strftime("%Y-%m-%d"),
        )

    if created_count > 0:
        await db.commit()
        logger.info("Generated %d recurring task(s) for user %s", created_count, user_id)

    return created_count
