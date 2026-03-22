"""
Goal Secretary action executor.

Parses structured actions from the LLM response and executes
CRUD operations on goals and tasks.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.task import Task

logger = logging.getLogger(__name__)


async def execute_actions(
    db: AsyncSession,
    user_id: uuid.UUID,
    actions: list[dict],
) -> list[str]:
    """
    Execute a list of goal/task actions and return a summary of results.

    Each action is a dict like:
      {"type": "create_goal", "title": "...", "description": "..."}
      {"type": "create_task", "goal_title": "...", "title": "..."}
      {"type": "update_goal", "goal_title": "...", "status": "completed"}
      {"type": "update_task", "task_title": "...", "status": "completed"}
      {"type": "delete_goal", "goal_title": "..."}
      {"type": "delete_task", "task_title": "..."}
    """
    results = []

    for action in actions:
        action_type = action.get("type", "")
        try:
            if action_type == "create_goal":
                msg = await _create_goal(db, user_id, action)
            elif action_type == "create_task":
                msg = await _create_task(db, user_id, action)
            elif action_type == "update_goal":
                msg = await _update_goal(db, user_id, action)
            elif action_type == "update_task":
                msg = await _update_task(db, user_id, action)
            elif action_type == "delete_goal":
                msg = await _delete_goal(db, user_id, action)
            elif action_type == "delete_task":
                msg = await _delete_task(db, user_id, action)
            else:
                msg = f"Unknown action type: {action_type}"
                logger.warning(msg)
            results.append(msg)
        except Exception as e:
            msg = f"Action '{action_type}' failed: {e}"
            logger.warning(msg)
            results.append(msg)

    if results:
        await db.commit()

    return results


# ── Action handlers ──────────────────────────────────


async def _create_goal(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    title = action.get("title", "").strip()
    if not title:
        return "Skipped create_goal: no title"

    goal = Goal(
        user_id=user_id,
        title=title,
        description=action.get("description", ""),
        status="active",
        due_at=_parse_date(action.get("due_at")),
        priority=action.get("priority", 0),
    )
    db.add(goal)
    await db.flush()  # get the ID without committing
    logger.info("Created goal '%s' (id=%s)", title, goal.id)
    return f"Created goal: {title}"


async def _create_task(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    title = action.get("title", "").strip()
    if not title:
        return "Skipped create_task: no title"

    # Link to a goal by title if provided
    goal_id = None
    goal_title = action.get("goal_title", "").strip()
    if goal_title:
        goal = await _find_goal_by_title(db, user_id, goal_title)
        if goal:
            goal_id = goal.id

    # Determine recurrence
    frequency = action.get("recurrence_frequency", "").strip().lower()
    if frequency in ("daily", "weekly", "monthly", "yearly"):
        recurrence = "recurring"
        due_at = None  # recurring tasks don't have deadlines
    else:
        recurrence = "one_time"
        frequency = None
        due_at = _parse_date(action.get("due_at"))

    task = Task(
        user_id=user_id,
        goal_id=goal_id,
        title=title,
        status="open",
        due_at=due_at,
        recurrence=recurrence,
        recurrence_frequency=frequency,
    )
    db.add(task)
    await db.flush()
    freq_label = f" ({frequency})" if frequency else ""
    logger.info("Created task '%s' (id=%s, goal=%s, recurrence=%s)", title, task.id, goal_id, recurrence)
    return f"Created task: {title}{freq_label}"


async def _update_goal(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    goal_title = action.get("goal_title", "").strip()
    if not goal_title:
        return "Skipped update_goal: no goal_title"

    goal = await _find_goal_by_title(db, user_id, goal_title)
    if not goal:
        return f"Goal not found: {goal_title}"

    if "status" in action:
        goal.status = action["status"]
    if "title" in action and action["title"] != goal_title:
        goal.title = action["title"]
    if "description" in action:
        goal.description = action["description"]

    logger.info("Updated goal '%s'", goal_title)
    return f"Updated goal: {goal_title}"


async def _update_task(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    task_title = action.get("task_title", "").strip()
    if not task_title:
        return "Skipped update_task: no task_title"

    task = await _find_task_by_title(db, user_id, task_title)
    if not task:
        return f"Task not found: {task_title}"

    if "status" in action:
        task.status = action["status"]
    if "title" in action and action["title"] != task_title:
        task.title = action["title"]
    if "due_at" in action:
        task.due_at = _parse_date(action["due_at"])

    logger.info("Updated task '%s'", task_title)
    return f"Updated task: {task_title}"


async def _delete_goal(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    goal_title = action.get("goal_title", "").strip()
    if not goal_title:
        return "Skipped delete_goal: no goal_title"

    goal = await _find_goal_by_title(db, user_id, goal_title)
    if not goal:
        return f"Goal not found: {goal_title}"

    await db.delete(goal)
    logger.info("Deleted goal '%s'", goal_title)
    return f"Deleted goal: {goal_title}"


async def _delete_task(db: AsyncSession, user_id: uuid.UUID, action: dict) -> str:
    task_title = action.get("task_title", "").strip()
    if not task_title:
        return "Skipped delete_task: no task_title"

    task = await _find_task_by_title(db, user_id, task_title)
    if not task:
        return f"Task not found: {task_title}"

    await db.delete(task)
    logger.info("Deleted task '%s'", task_title)
    return f"Deleted task: {task_title}"


# ── Lookup helpers ──────────────────────────────────


async def _find_goal_by_title(
    db: AsyncSession, user_id: uuid.UUID, title: str
) -> Goal | None:
    """Case-insensitive title match for goals."""
    result = await db.execute(
        select(Goal).where(
            Goal.user_id == user_id,
            Goal.title.ilike(title),
        )
    )
    return result.scalars().first()


async def _find_task_by_title(
    db: AsyncSession, user_id: uuid.UUID, title: str
) -> Task | None:
    """Case-insensitive title match for tasks."""
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.title.ilike(title),
        )
    )
    return result.scalars().first()


def _parse_date(val: str | None) -> datetime | None:
    """Try to parse an ISO date string, return None on failure."""
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None
