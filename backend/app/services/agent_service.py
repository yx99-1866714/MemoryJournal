"""
Agent service — CRUD operations and built-in agent seeding.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_thread import AgentThread, AgentMessage

logger = logging.getLogger(__name__)

# Built-in agent definitions
BUILTIN_AGENTS = [
    {
        "name": "Reflection Coach",
        "role": "reflection_coach",
        "purpose": "Help the user notice patterns and make sense of entries over time",
        "tone": "warm, curious, nonjudgmental",
        "memory_policy_json": {
            "use_episodic": True,
            "use_profile": True,
            "max_memories": 8,
            "time_window_days": 90,
        },
        "guardrails_json": {
            "no_diagnosis": True,
            "no_dependency_language": True,
            "crisis_safe_mode": True,
        },
        "output_schema_json": {
            "sections": [
                "today_summary",
                "pattern_connection",
                "supportive_observation",
                "next_step",
                "reflection_question",
            ]
        },
    },
    {
        "name": "Goal Secretary",
        "role": "goal_secretary",
        "purpose": "Track goals, tasks, and follow through on commitments mentioned in journals",
        "tone": "organized, encouraging, direct",
        "memory_policy_json": {
            "use_episodic": True,
            "use_profile": False,
            "max_memories": 8,
            "time_window_days": 30,
        },
        "guardrails_json": {
            "no_diagnosis": True,
            "no_dependency_language": True,
            "crisis_safe_mode": True,
        },
        "output_schema_json": {
            "sections": [
                "today_summary",
                "goals_identified",
                "progress_update",
                "next_step",
                "accountability_question",
            ]
        },
    },
    {
        "name": "Supportive Friend",
        "role": "supportive_friend",
        "purpose": "Provide emotional validation, warmth, and casual support",
        "tone": "warm, empathetic, casual",
        "memory_policy_json": {
            "use_episodic": True,
            "use_profile": True,
            "max_memories": 8,
            "time_window_days": 60,
        },
        "guardrails_json": {
            "no_diagnosis": True,
            "no_dependency_language": True,
            "crisis_safe_mode": True,
        },
        "output_schema_json": {
            "sections": [
                "today_summary",
                "emotional_reflection",
                "supportive_observation",
                "next_step",
                "reflection_question",
            ]
        },
    },
    {
        "name": "Inner Caregiver",
        "role": "inner_caregiver",
        "purpose": "Encourage self-compassion and gentle self-care through nurturing guidance",
        "tone": "gentle, nurturing, patient",
        "memory_policy_json": {
            "use_episodic": True,
            "use_profile": True,
            "max_memories": 8,
            "time_window_days": 90,
        },
        "guardrails_json": {
            "no_diagnosis": True,
            "no_dependency_language": True,
            "crisis_safe_mode": True,
            "no_parental_replacement": True,
        },
        "output_schema_json": {
            "sections": [
                "today_summary",
                "compassionate_reflection",
                "supportive_observation",
                "self_care_suggestion",
                "gentle_question",
            ]
        },
    },
]


async def seed_builtin_agents(db: AsyncSession) -> None:
    """Create built-in agents if they don't exist yet."""
    for agent_def in BUILTIN_AGENTS:
        result = await db.execute(
            select(Agent).where(Agent.role == agent_def["role"], Agent.is_builtin == True)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            agent = Agent(
                is_builtin=True,
                is_active=True,
                user_id=None,
                **agent_def,
            )
            db.add(agent)
            logger.info("Seeded built-in agent: %s", agent_def["name"])
    await db.commit()


async def get_agents(db: AsyncSession, user_id: uuid.UUID) -> list[Agent]:
    """Get all active agents: built-in + user's custom agents."""
    result = await db.execute(
        select(Agent).where(
            Agent.is_active == True,
            (Agent.is_builtin == True) | (Agent.user_id == user_id),
        ).order_by(Agent.is_builtin.desc(), Agent.created_at)
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    """Get a single agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_by_role(db: AsyncSession, role: str) -> Agent | None:
    """Get a built-in agent by role string."""
    result = await db.execute(
        select(Agent).where(Agent.role == role, Agent.is_builtin == True)
    )
    return result.scalar_one_or_none()


async def get_or_create_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    journal_id: uuid.UUID | None = None,
) -> AgentThread:
    """Find existing thread or create a new one."""
    query = select(AgentThread).where(
        AgentThread.user_id == user_id,
        AgentThread.agent_id == agent_id,
    )
    if journal_id:
        query = query.where(AgentThread.journal_id == journal_id)
    else:
        query = query.where(AgentThread.journal_id.is_(None))

    result = await db.execute(query)
    thread = result.scalars().first()

    if not thread:
        try:
            thread = AgentThread(
                user_id=user_id,
                agent_id=agent_id,
                journal_id=journal_id,
            )
            db.add(thread)
            await db.commit()
            await db.refresh(thread)
        except Exception:
            # Race condition: another concurrent call already created the thread
            await db.rollback()
            result = await db.execute(query)
            thread = result.scalars().first()

    return thread


async def get_thread_messages(
    db: AsyncSession, thread_id: uuid.UUID
) -> list[AgentMessage]:
    """Get all messages in a thread, ordered chronologically."""
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.thread_id == thread_id)
        .order_by(AgentMessage.created_at)
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    thread_id: uuid.UUID,
    role: str,
    content: str,
) -> AgentMessage:
    """Add a message to a thread."""
    msg = AgentMessage(thread_id=thread_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
