"""
Goals & Tasks API router — CRUD and summary for Phase 4.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db import get_db
from app.models.goal import Goal
from app.models.task import Task
from app.services.recurring_tasks import generate_recurring_tasks

router = APIRouter(prefix="/goals", tags=["goals"])


# ── Schemas ──────────────────────────────────────────

class GoalResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: str
    source_journal_id: str | None = None
    due_at: str | None = None
    priority: int = 0
    recurrence: str = "one_time"
    recurrence_frequency: str | None = None
    created_at: str
    tasks: list["TaskResponse"] = []

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
    goal_id: str | None = None
    source_journal_id: str | None = None
    due_at: str | None = None
    recurrence: str = "one_time"
    recurrence_frequency: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


class TaskUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    due_at: str | None = None  # ISO date string or null to clear


class GoalUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    description: str | None = None
    recurrence: str | None = None
    recurrence_frequency: str | None = None


class GoalsSummary(BaseModel):
    active_goals: int
    open_tasks: int
    overdue_tasks: int = 0
    due_today_tasks: int = 0
    recent_tasks: list[TaskResponse]


# ── Helpers ──────────────────────────────────────────

def _serialize_goal(goal: Goal, tasks: list[Task] | None = None) -> dict:
    return {
        "id": str(goal.id),
        "title": goal.title,
        "description": goal.description,
        "status": goal.status,
        "source_journal_id": str(goal.source_journal_id) if goal.source_journal_id else None,
        "due_at": goal.due_at.isoformat() if goal.due_at else None,
        "priority": goal.priority,
        "recurrence": goal.recurrence,
        "recurrence_frequency": goal.recurrence_frequency,
        "created_at": goal.created_at.isoformat(),
        "tasks": [_serialize_task(t) for t in (tasks or [])],
    }


def _serialize_task(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "goal_id": str(task.goal_id) if task.goal_id else None,
        "source_journal_id": str(task.source_journal_id) if task.source_journal_id else None,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "recurrence": task.recurrence,
        "recurrence_frequency": task.recurrence_frequency,
        "created_at": task.created_at.isoformat(),
    }


# ── Endpoints ────────────────────────────────────────

@router.get("/")
async def list_goals(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all goals with their tasks."""
    uid = uuid.UUID(user_id)

    # Auto-generate recurring tasks for the current period
    await generate_recurring_tasks(db, uid)
    result = await db.execute(
        select(Goal)
        .where(Goal.user_id == uid)
        .order_by(Goal.created_at.desc())
    )
    goals = list(result.scalars().all())

    response = []
    for goal in goals:
        task_result = await db.execute(
            select(Task)
            .where(Task.goal_id == goal.id)
            .order_by(Task.created_at)
        )
        tasks = list(task_result.scalars().all())
        response.append(_serialize_goal(goal, tasks))

    return {"goals": response}


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: str,
    body: GoalUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a goal's status, title, description, or recurrence."""
    result = await db.execute(
        select(Goal).where(
            Goal.id == uuid.UUID(goal_id),
            Goal.user_id == uuid.UUID(user_id),
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if body.status is not None:
        goal.status = body.status
    if body.title is not None:
        goal.title = body.title[:500]
    if body.description is not None:
        goal.description = body.description
    if body.recurrence is not None:
        if body.recurrence in ("one_time", "recurring"):
            goal.recurrence = body.recurrence
    if body.recurrence_frequency is not None:
        if body.recurrence_frequency in ("daily", "weekly", "monthly", "yearly"):
            goal.recurrence_frequency = body.recurrence_frequency
        else:
            goal.recurrence_frequency = None
    await db.commit()
    return _serialize_goal(goal)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a goal and its linked tasks."""
    result = await db.execute(
        select(Goal).where(
            Goal.id == uuid.UUID(goal_id),
            Goal.user_id == uuid.UUID(user_id),
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Delete tasks linked to this goal
    task_result = await db.execute(
        select(Task).where(Task.goal_id == goal.id)
    )
    for task in task_result.scalars().all():
        await db.delete(task)

    await db.delete(goal)
    await db.commit()


@router.get("/tasks")
async def list_tasks(
    status: str = "open",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List tasks, optionally filtered by status."""
    uid = uuid.UUID(user_id)
    query = select(Task).where(Task.user_id == uid)
    if status:
        query = query.where(Task.status == status)
    query = query.order_by(Task.created_at.desc())

    result = await db.execute(query)
    tasks = list(result.scalars().all())
    return {"tasks": [_serialize_task(t) for t in tasks]}


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a task's status, title, and/or deadline."""
    result = await db.execute(
        select(Task).where(
            Task.id == uuid.UUID(task_id),
            Task.user_id == uuid.UUID(user_id),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.status is not None:
        task.status = body.status
    if body.title is not None:
        task.title = body.title[:500]
    if body.due_at is not None:
        from datetime import datetime, timezone
        try:
            parsed = datetime.fromisoformat(body.due_at)
            # Store at noon UTC so ±12h timezone shifts don't change the day
            task.due_at = parsed.replace(hour=12, minute=0, second=0, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            task.due_at = None
    elif "due_at" in (body.model_fields_set or set()):
        task.due_at = None
    await db.commit()
    return _serialize_task(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    result = await db.execute(
        select(Task).where(
            Task.id == uuid.UUID(task_id),
            Task.user_id == uuid.UUID(user_id),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()


@router.get("/summary")
async def goals_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get summary counts and recent tasks for popup widget."""
    uid = uuid.UUID(user_id)

    # Active goals count
    goals_result = await db.execute(
        select(func.count()).select_from(Goal).where(
            Goal.user_id == uid, Goal.status == "active"
        )
    )
    active_goals = goals_result.scalar() or 0

    # Open tasks count
    tasks_count_result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == uid, Task.status == "open"
        )
    )
    open_tasks = tasks_count_result.scalar() or 0

    # Recent open tasks (top 5)
    recent_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid, Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(5)
    )
    recent_tasks = [_serialize_task(t) for t in recent_result.scalars().all()]

    # Overdue & due-today counts
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    tomorrow = now + timedelta(hours=24)

    overdue_result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == uid, Task.status == "open",
            Task.due_at.isnot(None), Task.due_at < now,
        )
    )
    overdue_count = overdue_result.scalar() or 0

    due_today_result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == uid, Task.status == "open",
            Task.due_at.isnot(None), Task.due_at >= now, Task.due_at < tomorrow,
        )
    )
    due_today_count = due_today_result.scalar() or 0

    return GoalsSummary(
        active_goals=active_goals,
        open_tasks=open_tasks,
        overdue_tasks=overdue_count,
        due_today_tasks=due_today_count,
        recent_tasks=recent_tasks,
    )


@router.get("/reminders")
async def get_reminders(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Return open tasks that need reminders:
    - overdue (past due_at)
    - due today (within 0–24 hours)
    - due tomorrow (within 24–48 hours)
    Filters out tasks already reminded within 12 hours.
    """
    from datetime import datetime, timedelta

    uid = uuid.UUID(user_id)
    now = datetime.utcnow()
    cutoff_48h = now + timedelta(hours=48)
    reminded_cutoff = now - timedelta(hours=12)

    # Fetch open tasks with a due_at within the next 48h or already overdue
    result = await db.execute(
        select(Task).where(
            Task.user_id == uid,
            Task.status == "open",
            Task.due_at.isnot(None),
            Task.due_at <= cutoff_48h,
        ).order_by(Task.due_at)
    )
    tasks = list(result.scalars().all())

    reminders = []
    task_ids_to_update = []

    for task in tasks:
        # Skip if already reminded recently
        if task.last_reminded_at and task.last_reminded_at > reminded_cutoff:
            continue

        # Categorize urgency
        if task.due_at < now:
            urgency = "overdue"
        elif task.due_at < now + timedelta(hours=24):
            urgency = "today"
        else:
            urgency = "tomorrow"

        reminders.append({
            "id": str(task.id),
            "title": task.title,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "urgency": urgency,
            "goal_id": str(task.goal_id) if task.goal_id else None,
        })
        task_ids_to_update.append(task)

    # Mark tasks as reminded
    for task in task_ids_to_update:
        task.last_reminded_at = now
    if task_ids_to_update:
        await db.commit()

    return {"reminders": reminders, "count": len(reminders)}

