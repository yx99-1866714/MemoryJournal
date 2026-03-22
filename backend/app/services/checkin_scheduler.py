"""
Proactive check-in scheduler.

Runs periodically to generate proactive check-in messages from agents.
Frequency is adjusted based on the user's emotional state:
  - critical: every 1 hour
  - elevated: every 24 hours
  - normal: every 7 days (168 hours)
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.models.agent import Agent
from app.models.agent_thread import AgentThread, AgentMessage
from app.models.journal import Journal
from app.models.user import User

logger = logging.getLogger(__name__)

# Frequency mapping: urgency → minimum hours between check-ins
FREQUENCY_HOURS = {
    "critical": 1,
    "elevated": 24,
    "normal": 168,  # 7 days
}

# Role-specific instructions for proactive check-ins
ROLE_INSTRUCTIONS = {
    "goal_secretary": (
        "You are checking in about the user's goals and tasks. "
        "If they have new goals that haven't been broken down into tasks, offer to help. "
        "If there are upcoming deadlines, remind them gently. "
        "If tasks are overdue, acknowledge it without being pushy."
    ),
    "supportive_friend": (
        "You are checking in because you care about the user's wellbeing. "
        "Be casual, warm, and emotionally attuned. "
        "If they seem to be going through a tough time, acknowledge their feelings. "
        "If things seem normal, just be a friendly presence."
    ),
    "inner_caregiver": (
        "You are gently checking in on the user's self-care and emotional needs. "
        "Encourage self-compassion. If they seem stressed or overwhelmed, "
        "suggest a small self-care action. Be nurturing but not overbearing."
    ),
    "reflection_coach": (
        "You are reaching out to help the user reflect on recent patterns. "
        "If you notice recurring themes in their journals, gently point them out. "
        "If they haven't journaled recently, encourage them without pressure."
    ),
}


async def run_proactive_checkins():
    """
    Main entry point. Called periodically by the scheduler.
    Iterates over all users and generates proactive check-ins as needed.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.debug("No OpenRouter API key, skipping proactive check-ins")
        return

    # Get all users in their own session
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(User))
            users = list(result.scalars().all())
            user_ids = [u.id for u in users]
    except Exception as e:
        logger.exception("Proactive check-in scheduler error (fetch users): %s", e)
        return

    for uid in user_ids:
        try:
            await _process_user_checkins(uid)
        except Exception as e:
            logger.warning(
                "Failed to process check-ins for user %s: %s",
                uid, e,
            )


async def _process_user_checkins(user_id: uuid.UUID):
    """Process proactive check-ins for a single user."""
    from app.services import llm_service

    now = datetime.now(timezone.utc)

    # Use a fresh session for reading context
    async with SessionLocal() as db:
        # Get active built-in agents
        result = await db.execute(
            select(Agent).where(Agent.is_builtin == True, Agent.is_active == True)
        )
        agents = list(result.scalars().all())
        if not agents:
            return

        agent_data = [
            {"id": a.id, "name": a.name, "role": a.role, "purpose": a.purpose, "tone": a.tone}
            for a in agents
        ]

        # Gather user context: recent journals (last 7 days)
        week_ago = now - timedelta(days=7)
        journal_result = await db.execute(
            select(Journal)
            .where(Journal.user_id == user_id, Journal.created_at >= week_ago)
            .order_by(Journal.created_at.desc())
            .limit(5)
        )
        recent_journals = list(journal_result.scalars().all())

        if not recent_journals:
            return

        journal_texts = [j.raw_text[:500] for j in recent_journals if j.raw_text]

        # Gather recent chat excerpts
        chat_excerpts = []
        for ad in agent_data:
            thread_q = select(AgentThread).where(
                AgentThread.user_id == user_id,
                AgentThread.agent_id == ad["id"],
                AgentThread.journal_id.is_(None),
            )
            thread_result = await db.execute(thread_q)
            thread = thread_result.scalars().first()
            if thread:
                msg_result = await db.execute(
                    select(AgentMessage)
                    .where(AgentMessage.thread_id == thread.id)
                    .order_by(AgentMessage.created_at.desc())
                    .limit(3)
                )
                for msg in msg_result.scalars().all():
                    chat_excerpts.append(f"{msg.role}: {msg.content[:200]}")

        # Build goals context
        goals_context = await _build_goals_context(db, user_id)

    # Analyze emotional state (outside DB session — pure LLM call)
    emotional_state = await llm_service.analyze_emotional_state(
        recent_journals=journal_texts,
        recent_chat_excerpts=chat_excerpts[:10],
        goals_context=goals_context,
    )

    urgency = emotional_state["urgency"]
    min_hours = FREQUENCY_HOURS.get(urgency, 168)
    cutoff = now - timedelta(hours=min_hours)

    logger.info(
        "User %s: urgency=%s, min_hours=%d",
        user_id, urgency, min_hours,
    )

    # Generate check-in for each agent (each gets its own session)
    for ad in agent_data:
        try:
            await _maybe_checkin_agent(
                ad, user_id, cutoff, now,
                journal_texts, goals_context, urgency, emotional_state["summary"],
            )
        except Exception as e:
            logger.warning(
                "Failed check-in for agent '%s' user %s: %s",
                ad["name"], user_id, e,
            )


async def _maybe_checkin_agent(
    agent_data: dict,
    user_id: uuid.UUID,
    cutoff: datetime,
    now: datetime,
    journal_texts: list[str],
    goals_context: str,
    urgency: str,
    emotional_summary: str,
):
    """Generate a proactive check-in for one agent if it's time."""
    from app.services import llm_service

    agent_id = agent_data["id"]

    # Check if we should send a check-in (use own session)
    async with SessionLocal() as db:
        # Get or create the free-chat thread
        query = select(AgentThread).where(
            AgentThread.user_id == user_id,
            AgentThread.agent_id == agent_id,
            AgentThread.journal_id.is_(None),
        )
        result = await db.execute(query)
        thread = result.scalars().first()

        if not thread:
            thread = AgentThread(
                user_id=user_id,
                agent_id=agent_id,
                journal_id=None,
            )
            db.add(thread)
            await db.commit()
            await db.refresh(thread)

        # Check if we already sent a proactive message recently
        if thread.last_proactive_checkin_at and thread.last_proactive_checkin_at > cutoff:
            return  # Too soon

        thread_id = thread.id

    # Build context for this agent (no DB needed)
    context_parts = [f"Emotional state: {emotional_summary} (urgency: {urgency})"]
    for i, jt in enumerate(journal_texts[:3], 1):
        context_parts.append(f"Recent journal {i}: {jt}")
    if goals_context and agent_data["role"] == "goal_secretary":
        context_parts.append(f"Goals/Tasks: {goals_context}")

    context = "\n\n".join(context_parts)
    role_instructions = ROLE_INSTRUCTIONS.get(agent_data["role"], "")

    # Generate the proactive message (pure LLM call, no DB)
    llm_result = await llm_service.generate_proactive_checkin(
        agent_config=agent_data,
        context=context,
        role_specific_instructions=role_instructions,
    )

    # Store the message and update timestamp (use own session)
    async with SessionLocal() as db:
        msg = AgentMessage(thread_id=thread_id, role="assistant", content=llm_result["response_text"])
        db.add(msg)

        # Update last_proactive_checkin_at
        result = await db.execute(
            select(AgentThread).where(AgentThread.id == thread_id)
        )
        thread = result.scalars().first()
        if thread:
            thread.last_proactive_checkin_at = now

        await db.commit()

    logger.info(
        "Proactive check-in sent: agent='%s', user=%s, urgency=%s",
        agent_data["name"], user_id, urgency,
    )


async def _build_goals_context(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Build a summary string of goals and tasks for the Goal Secretary."""
    from app.models.goal import Goal
    from app.models.task import Task

    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    # Active goals
    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.status == "active")
        .limit(10)
    )
    goals = list(goals_result.scalars().all())

    # Open tasks with deadlines
    tasks_result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id, Task.status.in_(["open", "in_progress"]))
        .order_by(Task.due_at.asc().nulls_last())
        .limit(15)
    )
    tasks = list(tasks_result.scalars().all())

    parts = []
    if goals:
        parts.append(f"{len(goals)} active goal(s): " + ", ".join(g.title for g in goals))

    overdue = [t for t in tasks if t.due_at and t.due_at < now]
    due_soon = [t for t in tasks if t.due_at and now <= t.due_at <= tomorrow]
    open_tasks = [t for t in tasks if not t.due_at or t.due_at > tomorrow]

    if overdue:
        parts.append(f"OVERDUE tasks: " + ", ".join(f"'{t.title}'" for t in overdue))
    if due_soon:
        parts.append(f"Due today/tomorrow: " + ", ".join(f"'{t.title}'" for t in due_soon))
    if open_tasks:
        parts.append(f"{len(open_tasks)} other open task(s)")

    return "; ".join(parts) if parts else ""


async def start_scheduler_loop():
    """
    Background loop that runs proactive check-ins every 30 minutes.
    Designed to be started as an asyncio task in the FastAPI lifespan.
    """
    logger.info("Proactive check-in scheduler started (every 30 minutes)")
    while True:
        try:
            await run_proactive_checkins()
        except Exception as e:
            logger.exception("Scheduler loop error: %s", e)
        await asyncio.sleep(30 * 60)  # 30 minutes
