"""
Journal processing pipeline.

Orchestrates: submit to EverMemOS → poll status → retrieve memories → LLM feedback → store.
Designed to run as a FastAPI background task.
"""
import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.models.journal import Journal
from app.models.journal_feedback import JournalFeedback
from app.services import evermemos
from app.services import llm_service

logger = logging.getLogger(__name__)

MAX_POLL_SECONDS = 30
POLL_INTERVAL = 2.0


async def process_journal(
    journal_id: str,
    user_id: str,
    user_name: str = "User",
    selected_agent_id: str | None = None,
    skip_checkins: bool = False,
):
    """
    Full pipeline for processing a submitted journal entry.

    This runs as a background task after journal submission.
    It creates its own database session to avoid lifecycle issues.
    """
    async with SessionLocal() as db:
        try:
            await _process(db, journal_id, user_id, user_name, selected_agent_id, skip_checkins)
        except Exception as e:
            logger.exception("Failed to process journal %s: %s", journal_id, e)
            # Mark journal as failed
            try:
                await db.rollback()
                journal = await _get_journal(db, journal_id)
                if journal:
                    journal.status = "failed"
                    journal.evermemos_status = f"error: {str(e)[:450]}"
                    await db.commit()
            except Exception:
                logger.exception("Failed to mark journal %s as failed", journal_id)


async def _get_journal(db: AsyncSession, journal_id: str) -> Journal | None:
    result = await db.execute(
        select(Journal).where(Journal.id == uuid.UUID(journal_id))
    )
    return result.scalar_one_or_none()


async def _load_agent(db: AsyncSession, agent_id: str | None):
    """Load agent from DB, fallback to Reflection Coach."""
    from app.models.agent import Agent

    if agent_id:
        result = await db.execute(
            select(Agent).where(Agent.id == uuid.UUID(agent_id))
        )
        agent = result.scalar_one_or_none()
        if agent:
            return agent

    # Fallback to built-in Reflection Coach
    result = await db.execute(
        select(Agent).where(Agent.role == "reflection_coach", Agent.is_builtin == True)
    )
    return result.scalar_one_or_none()


async def _process(
    db: AsyncSession,
    journal_id: str,
    user_id: str,
    user_name: str,
    selected_agent_id: str | None = None,
    skip_checkins: bool = False,
):
    journal = await _get_journal(db, journal_id)
    if not journal:
        logger.error("Journal %s not found", journal_id)
        return

    # Load the selected agent
    agent = await _load_agent(db, selected_agent_id)
    agent_config = None
    agent_role = "reflection_coach"
    agent_db_id = None

    if agent:
        agent_config = {
            "name": agent.name,
            "role": agent.role,
            "purpose": agent.purpose,
            "tone": agent.tone,
        }
        agent_role = agent.role
        agent_db_id = agent.id
        logger.info("Using agent '%s' for journal %s", agent.name, journal_id)

    # Step 0: Auto-generate title if missing
    if not journal.title and settings.OPENROUTER_API_KEY:
        try:
            title = await llm_service.generate_title(journal.raw_text)
            journal.title = title
            await db.commit()
            logger.info("Auto-generated title for journal %s: %s", journal_id, title)
        except Exception as e:
            logger.warning("Failed to auto-generate title: %s", e)

    # Step 0.5: Auto-generate tags
    if settings.OPENROUTER_API_KEY:
        try:
            await _generate_and_link_tags(db, journal, user_id)
        except Exception as e:
            logger.warning("Failed to auto-generate tags: %s", e)

    # Step 1: Submit to EverMemOS (if API key is configured)
    memories = []
    if settings.EVERMEMOS_API_KEY:
        logger.info("Submitting journal %s to EverMemOS", journal_id)
        try:
            submit_resp = await evermemos.submit_memory(
                content=journal.raw_text,
                user_id=user_id,
                journal_id=journal_id,
                user_name=user_name,
            )
            request_id = submit_resp.get("request_id")
            journal.evermemos_request_id = request_id
            journal.evermemos_status = "queued"
            await db.commit()

            # Step 2: Poll for completion
            if request_id:
                elapsed = 0.0
                while elapsed < MAX_POLL_SECONDS:
                    await asyncio.sleep(POLL_INTERVAL)
                    elapsed += POLL_INTERVAL
                    status_resp = await evermemos.get_request_status(request_id)
                    em_status = status_resp.get("status", "unknown")
                    journal.evermemos_status = em_status
                    await db.commit()

                    if em_status in ("completed", "done", "processed"):
                        break
                    if em_status in ("failed", "error"):
                        logger.warning("EverMemOS processing failed for %s", journal_id)
                        break

            # Step 3: Retrieve relevant memories
            memories = await evermemos.search_memories(
                query=journal.raw_text[:500],  # use first 500 chars as query
                user_id=user_id,
                max_results=8,
                memory_types=["episodic", "profile"],
            )
        except Exception as e:
            logger.warning("EverMemOS integration error (non-fatal): %s", e)
            journal.evermemos_status = f"error: {str(e)[:450]}"
            await db.commit()
    else:
        logger.info("EverMemOS API key not configured, skipping memory submission")

    # Mark journal as processed (feedback generation removed — no longer used in frontend)
    journal.status = "processed"
    await db.commit()
    logger.info("Journal %s processed successfully", journal_id)

    # Step 5.5: Extract goals and tasks from journal
    if settings.OPENROUTER_API_KEY:
        try:
            extracted = await llm_service.extract_goals_tasks(journal.raw_text)
            await _store_goals_tasks(
                db, extracted, user_id=user_id, journal_id=journal_id
            )
        except Exception as e:
            logger.warning("Goals/tasks extraction failed (non-fatal): %s", e)

    # Step 6: Generate proactive check-in messages from all agents
    # (skipped during bulk import for older journals to save LLM calls)
    if settings.OPENROUTER_API_KEY and not skip_checkins:
        await _generate_agent_checkins(
            db, journal, user_id, memories
        )
    elif skip_checkins:
        logger.info("Skipping agent check-ins for journal %s (bulk import)", journal_id)


async def _generate_agent_checkins(
    db: AsyncSession,
    journal: Journal,
    user_id: str,
    memories: list,
):
    """Generate proactive check-in messages from all agents (built-in + user custom) for this journal."""
    from app.models.agent import Agent
    from app.services import agent_service
    from sqlalchemy import or_

    result = await db.execute(
        select(Agent).where(
            Agent.is_active == True,
            or_(
                Agent.is_builtin == True,
                Agent.user_id == uuid.UUID(user_id),
            ),
        )
    )
    all_agents = list(result.scalars().all())

    async def _checkin_for_agent(agent: Agent):
        try:
            agent_config = {
                "name": agent.name,
                "role": agent.role,
                "purpose": agent.purpose,
                "tone": agent.tone,
            }
            checkin = await llm_service.generate_checkin_message(
                journal_text=journal.raw_text,
                memories=memories,
                agent_config=agent_config,
            )

            # Create a journal-scoped thread and store the check-in message
            thread = await agent_service.get_or_create_thread(
                db,
                user_id=uuid.UUID(user_id),
                agent_id=agent.id,
                journal_id=journal.id,
            )
            await agent_service.add_message(
                db, thread.id, "assistant", checkin["response_text"]
            )
            logger.info(
                "Agent '%s' sent check-in for journal %s",
                agent.name,
                str(journal.id),
            )
        except Exception as e:
            logger.warning(
                "Failed to generate check-in from '%s': %s", agent.name, e
            )

    # Run all check-in generations concurrently
    await asyncio.gather(*[_checkin_for_agent(a) for a in all_agents])
    logger.info("All agent check-ins completed for journal %s", str(journal.id))


async def _store_goals_tasks(
    db: AsyncSession,
    extracted: dict,
    user_id: str,
    journal_id: str,
):
    """Store extracted goals and tasks in the database."""
    from datetime import datetime, timezone
    from sqlalchemy import delete
    from app.models.goal import Goal
    from app.models.task import Task

    uid = uuid.UUID(user_id)
    jid = uuid.UUID(journal_id)

    # Delete any existing goals and tasks for this journal (for re-processing edits)
    await db.execute(delete(Goal).where(Goal.source_journal_id == jid))
    await db.execute(delete(Task).where(Task.source_journal_id == jid))

    def _parse_due_date(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            # Store at noon UTC so ±12h timezone shifts don't change the day
            return datetime.strptime(raw, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    for g in extracted.get("goals", []):
        if not g.get("title"):
            continue
        recurrence = g.get("recurrence", "one_time")
        if recurrence not in ("one_time", "recurring"):
            recurrence = "one_time"
        freq = g.get("recurrence_frequency")
        if freq not in ("daily", "weekly", "monthly", "yearly", None):
            freq = None
        goal = Goal(
            user_id=uid,
            title=g["title"][:500],
            description=g.get("description", ""),
            source_journal_id=jid,
            recurrence=recurrence,
            recurrence_frequency=freq,
            due_at=_parse_due_date(g.get("due_date")),
        )
        db.add(goal)

    for t in extracted.get("tasks", []):
        if not t.get("title"):
            continue
        recurrence = t.get("recurrence", "one_time")
        if recurrence not in ("one_time", "recurring"):
            recurrence = "one_time"
        freq = t.get("recurrence_frequency")
        if freq not in ("daily", "weekly", "monthly", "yearly", None):
            freq = None
        task = Task(
            user_id=uid,
            title=t["title"][:500],
            source_journal_id=jid,
            recurrence=recurrence,
            recurrence_frequency=freq,
            due_at=_parse_due_date(t.get("due_date")),
        )
        db.add(task)

    await db.commit()
    logger.info(
        "Stored %d goals and %d tasks for journal %s",
        len(extracted.get("goals", [])),
        len(extracted.get("tasks", [])),
        journal_id,
    )


async def _generate_and_link_tags(
    db: AsyncSession,
    journal: Journal,
    user_id: str,
):
    """Generate tags for a journal and link them via journal_tags."""
    from app.models.tag import Tag, journal_tags

    uid = uuid.UUID(user_id)

    # Fetch existing user tags for reuse
    result = await db.execute(
        select(Tag).where(Tag.user_id == uid)
    )
    existing_tags_objs = list(result.scalars().all())
    existing_names = [t.name for t in existing_tags_objs]

    # Ask LLM
    tag_names = await llm_service.generate_tags(journal.raw_text, existing_names)
    if not tag_names:
        return

    # Remove existing associations for this journal (for re-processing)
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(journal_tags).where(journal_tags.c.journal_id == journal.id)
    )

    # Map existing tag names (lowercase) -> Tag objects
    existing_map = {t.name.lower(): t for t in existing_tags_objs}

    for name in tag_names:
        tag_obj = existing_map.get(name.lower())
        if not tag_obj:
            tag_obj = Tag(user_id=uid, name=name.lower())
            db.add(tag_obj)
            await db.flush()  # ensure tag_obj.id is populated
            existing_map[name.lower()] = tag_obj

        # Insert association
        await db.execute(
            journal_tags.insert().values(
                journal_id=journal.id, tag_id=tag_obj.id
            )
        )

    await db.commit()
    logger.info("Linked %d tags to journal %s: %s", len(tag_names), str(journal.id), tag_names)
