"""
Agents API router — list agents, follow-up chat.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
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
    agents = await agent_service.get_agents(db, uuid.UUID(user_id))
    return AgentListResponse(agents=[AgentResponse.model_validate(a) for a in agents])


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
    _logger.info("Agent respond: tz_offset_minutes=%s", body.tz_offset_minutes)

    # Generate response
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
