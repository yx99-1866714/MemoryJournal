"""
Agents API router — list agents, follow-up chat.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.config import settings
from app.db import get_db
from app.models.journal import Journal
from app.schemas.agent import (
    AgentCreateRequest,
    AgentListResponse,
    AgentRespondRequest,
    AgentResponse,
    AgentUpdateRequest,
    MessageResponse,
    ThreadResponse,
)
from app.services import agent_service
from app.services import llm_service
from app.services import evermemos

from sqlalchemy import select

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.agent_thread import AgentThread, AgentMessage

    agents = await agent_service.get_agents(db, uuid.UUID(user_id))

    # Compute unread counts per agent (graceful degradation if columns missing)
    agent_responses = []
    for a in agents:
        unread = 0
        try:
            # Find the canonical free-chat thread for this agent/user
            # (most recently updated, to exclude orphaned journal threads)
            thread_q = (
                select(AgentThread)
                .where(
                    AgentThread.user_id == uuid.UUID(user_id),
                    AgentThread.agent_id == a.id,
                    AgentThread.journal_id.is_(None),
                )
                .order_by(AgentThread.updated_at.desc())
                .limit(1)
            )
            thread_result = await db.execute(thread_q)
            thread = thread_result.scalars().first()

            if thread:
                if thread.last_read_at:
                    # Count messages newer than last read
                    msg_q = select(func.count()).select_from(AgentMessage).where(
                        AgentMessage.thread_id == thread.id,
                        AgentMessage.role == "assistant",
                        AgentMessage.created_at > thread.last_read_at,
                    )
                else:
                    # Never read — all assistant messages are unread
                    msg_q = select(func.count()).select_from(AgentMessage).where(
                        AgentMessage.thread_id == thread.id,
                        AgentMessage.role == "assistant",
                    )
                unread = (await db.execute(msg_q)).scalar_one()
        except Exception:
            await db.rollback()
            unread = 0

        resp = AgentResponse.model_validate(a)
        resp.unread_count = unread
        agent_responses.append(resp)

    return AgentListResponse(agents=agent_responses)


@router.get("/unread-total")
async def get_unread_total(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return total unread assistant messages across all agents."""
    import logging
    logger = logging.getLogger(__name__)
    from app.models.agent_thread import AgentThread, AgentMessage
    from app.models.agent import Agent

    try:
        # Get all active agents for this user (built-in + user-created)
        from sqlalchemy import or_
        agents_q = select(Agent).where(
            Agent.is_active == True,
            or_(Agent.is_builtin == True, Agent.user_id == uuid.UUID(user_id)),
        )
        agents_result = await db.execute(agents_q)
        agents = list(agents_result.scalars().all())

        total = 0
        for agent in agents:
            # Find the canonical free-chat thread for this agent
            # (the one used by the scheduler/ChatWindow, ordered by most recently used)
            thread_q = (
                select(AgentThread)
                .where(
                    AgentThread.user_id == uuid.UUID(user_id),
                    AgentThread.agent_id == agent.id,
                    AgentThread.journal_id.is_(None),
                )
                .order_by(AgentThread.updated_at.desc())
                .limit(1)
            )
            thread_result = await db.execute(thread_q)
            thread = thread_result.scalars().first()
            if not thread:
                continue

            if thread.last_read_at:
                msg_q = select(func.count()).select_from(AgentMessage).where(
                    AgentMessage.thread_id == thread.id,
                    AgentMessage.role == "assistant",
                    AgentMessage.created_at > thread.last_read_at,
                )
            else:
                msg_q = select(func.count()).select_from(AgentMessage).where(
                    AgentMessage.thread_id == thread.id,
                    AgentMessage.role == "assistant",
                )
            count = (await db.execute(msg_q)).scalar_one()
            if count > 0:
                logger.info("Unread: agent=%s, thread=%s, last_read=%s, count=%d",
                           agent.name, thread.id, thread.last_read_at, count)
            total += count

        return {"unread_total": total}
    except Exception:
        await db.rollback()
        return {"unread_total": 0}


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    agent = await agent_service.get_agent(db, uuid.UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom user-owned agent."""
    from app.models.agent import Agent
    import re

    # Generate a unique role slug from the name
    role_slug = re.sub(r'[^a-z0-9]+', '_', body.name.lower()).strip('_')
    role_slug = f"custom_{role_slug}_{uuid.uuid4().hex[:6]}"

    agent = Agent(
        user_id=uuid.UUID(user_id),
        name=body.name,
        role=role_slug,
        purpose=body.purpose,
        tone=body.tone,
        system_prompt=body.system_prompt,
        is_builtin=False,
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom agent. Built-in agents cannot be edited."""
    agent = await agent_service.get_agent(db, uuid.UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.is_builtin:
        raise HTTPException(status_code=403, detail="Built-in agents cannot be edited")
    if agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=403, detail="Not your agent")

    for field in ["name", "purpose", "tone", "system_prompt", "is_active"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(agent, field, val)

    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}/toggle", response_model=AgentResponse)
async def toggle_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Toggle agent active/inactive. Works for both built-in and custom agents."""
    agent = await agent_service.get_agent(db, uuid.UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    # Custom agents must belong to this user
    if not agent.is_builtin and agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=403, detail="Not your agent")

    agent.is_active = not agent.is_active
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom agent and its threads/messages."""
    from app.models.agent_thread import AgentMessage, AgentThread

    agent = await agent_service.get_agent(db, uuid.UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.is_builtin:
        raise HTTPException(status_code=403, detail="Built-in agents cannot be deleted")
    if agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=403, detail="Not your agent")

    # Cascade delete threads and messages
    threads_result = await db.execute(
        select(AgentThread).where(AgentThread.agent_id == uuid.UUID(agent_id))
    )
    for thread in threads_result.scalars().all():
        await db.execute(
            delete(AgentMessage).where(AgentMessage.thread_id == thread.id)
        )
        await db.delete(thread)

    await db.delete(agent)
    await db.commit()

@router.post("/{agent_id}/respond", response_model=MessageResponse)
async def agent_respond(
    agent_id: str,
    body: AgentRespondRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a follow-up message and get an agent response."""
    agent = await agent_service.get_agent(db, uuid.UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get or create thread
    thread = await agent_service.get_or_create_thread(
        db,
        user_id=uuid.UUID(user_id),
        agent_id=uuid.UUID(agent_id),
        journal_id=body.journal_id,
    )

    # Load journal context if available
    journal_text = ""
    if body.journal_id:
        result = await db.execute(
            select(Journal).where(
                Journal.id == body.journal_id,
                Journal.user_id == uuid.UUID(user_id),
            )
        )
        journal = result.scalar_one_or_none()
        if journal:
            journal_text = journal.raw_text

    # Store user message
    await agent_service.add_message(db, thread.id, "user", body.message)

    # Get thread history
    messages = await agent_service.get_thread_messages(db, thread.id)

    # Retrieve memories for context — use user's message or journal text as query
    memories = []
    search_query = journal_text[:500] if journal_text else body.message[:500]
    if settings.EVERMEMOS_API_KEY and search_query:
        try:
            memories = await evermemos.search_memories(
                query=search_query,
                user_id=user_id,
                max_results=8,
            )
        except Exception:
            pass  # non-fatal

    # Build agent config from DB agent
    agent_config = {
        "name": agent.name,
        "role": agent.role,
        "purpose": agent.purpose,
        "tone": agent.tone,
    }

    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("Agent respond: tz_offset_minutes=%s, role=%s", body.tz_offset_minutes, agent.role)

    # Route Goal Secretary through structured tool-use flow
    if agent.role == "goal_secretary":
        from app.services.goal_actions import execute_actions

        # Build goals/tasks context for the LLM
        goals_context = await _build_goals_context_for_agent(db, uuid.UUID(user_id))

        result = await llm_service.generate_goal_secretary_response(
            thread_messages=messages,
            goals_context=goals_context,
            journal_text=journal_text,
            memories=memories,
            agent_config=agent_config,
            tz_offset_minutes=body.tz_offset_minutes,
        )

        # Execute any actions the LLM requested
        actions = result.get("actions", [])
        if actions:
            action_results = await execute_actions(db, uuid.UUID(user_id), actions)
            _logger.info("Goal Secretary actions executed: %s", action_results)
    else:
        # Standard chat flow for all other agents
        result = await llm_service.generate_chat_response(
            thread_messages=messages,
            journal_text=journal_text,
            memories=memories,
            agent_config=agent_config,
            tz_offset_minutes=body.tz_offset_minutes,
        )

    # Store assistant message
    assistant_msg = await agent_service.add_message(
        db, thread.id, "assistant", result["response_text"]
    )

    return MessageResponse.model_validate(assistant_msg)


async def _build_goals_context_for_agent(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Build a comprehensive text summary of goals and tasks for the Goal Secretary."""
    from app.models.goal import Goal
    from app.models.task import Task

    # Fetch active goals
    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.status.in_(["active", "paused"]))
        .order_by(Goal.created_at.desc())
        .limit(20)
    )
    goals = list(goals_result.scalars().all())

    # Fetch all open/in-progress tasks
    tasks_result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id, Task.status.in_(["open", "in_progress"]))
        .order_by(Task.due_at.asc().nulls_last())
        .limit(50)
    )
    tasks = list(tasks_result.scalars().all())

    # Build text representation
    parts = []
    for goal in goals:
        goal_tasks = [t for t in tasks if t.goal_id == goal.id]
        due_str = f" (due: {goal.due_at.strftime('%Y-%m-%d')})" if goal.due_at else ""
        parts.append(f"Goal: \"{goal.title}\" [{goal.status}]{due_str}")
        if goal.description:
            parts.append(f"  Description: {goal.description[:200]}")
        for t in goal_tasks:
            t_due = f" (due: {t.due_at.strftime('%Y-%m-%d')})" if t.due_at else ""
            t_freq = f" (recurring: {t.recurrence_frequency})" if t.recurrence == "recurring" else ""
            parts.append(f"  - Task: \"{t.title}\" [{t.status}]{t_due}{t_freq}")

    # Tasks without a goal
    orphan_tasks = [t for t in tasks if not t.goal_id]
    if orphan_tasks:
        parts.append("\nStandalone Tasks (no goal):")
        for t in orphan_tasks:
            t_due = f" (due: {t.due_at.strftime('%Y-%m-%d')})" if t.due_at else ""
            t_freq = f" (recurring: {t.recurrence_frequency})" if t.recurrence == "recurring" else ""
            parts.append(f"  - Task: \"{t.title}\" [{t.status}]{t_due}{t_freq}")

    if not parts:
        return "The user has no active goals or tasks."

    return "\n".join(parts)

@router.get("/{agent_id}/threads", response_model=ThreadResponse | None)
async def get_thread(
    agent_id: str,
    journal_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the thread (with messages) for a given agent + journal combo."""
    from app.models.agent_thread import AgentThread

    query = select(AgentThread).where(
        AgentThread.user_id == uuid.UUID(user_id),
        AgentThread.agent_id == uuid.UUID(agent_id),
    )
    if journal_id:
        query = query.where(AgentThread.journal_id == uuid.UUID(journal_id))
    else:
        query = query.where(AgentThread.journal_id.is_(None))

    result = await db.execute(query)
    thread = result.scalars().first()

    if not thread:
        return None

    messages = await agent_service.get_thread_messages(db, thread.id)
    return ThreadResponse(
        id=thread.id,
        agent_id=thread.agent_id,
        journal_id=thread.journal_id,
        messages=[MessageResponse.model_validate(m) for m in messages],
        created_at=thread.created_at,
    )


@router.delete("/{agent_id}/threads", status_code=status.HTTP_204_NO_CONTENT)
async def clear_thread(
    agent_id: str,
    journal_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete all messages in a thread (and the thread itself)."""
    from app.models.agent_thread import AgentMessage, AgentThread

    query = select(AgentThread).where(
        AgentThread.user_id == uuid.UUID(user_id),
        AgentThread.agent_id == uuid.UUID(agent_id),
    )
    if journal_id:
        query = query.where(AgentThread.journal_id == uuid.UUID(journal_id))
    else:
        query = query.where(AgentThread.journal_id.is_(None))

    result = await db.execute(query)
    threads = list(result.scalars().all())

    for thread in threads:
        await db.execute(
            delete(AgentMessage).where(AgentMessage.thread_id == thread.id)
        )
        await db.delete(thread)
    if threads:
        await db.commit()


@router.post("/{agent_id}/threads/read", status_code=200)
async def mark_thread_read(
    agent_id: str,
    journal_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a thread as read by setting last_read_at to now."""
    import logging
    logger = logging.getLogger(__name__)
    from datetime import datetime, timezone
    from app.models.agent_thread import AgentThread

    query = (
        select(AgentThread)
        .where(
            AgentThread.user_id == uuid.UUID(user_id),
            AgentThread.agent_id == uuid.UUID(agent_id),
        )
    )
    if journal_id:
        query = query.where(AgentThread.journal_id == uuid.UUID(journal_id))
    else:
        # Get the canonical free-chat thread (most recently updated)
        query = query.where(AgentThread.journal_id.is_(None)).order_by(AgentThread.updated_at.desc()).limit(1)

    result = await db.execute(query)
    thread = result.scalars().first()

    if thread:
        now = datetime.now(timezone.utc)
        logger.info("mark_thread_read: agent=%s, thread=%s, old_last_read=%s, new_last_read=%s",
                   agent_id, thread.id, thread.last_read_at, now)
        thread.last_read_at = now
        await db.commit()
        return {"status": "ok"}
    else:
        logger.warning("mark_thread_read: NO thread found for agent=%s, user=%s, journal_id=%s",
                      agent_id, user_id, journal_id)

    return {"status": "no_thread"}
