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


async def process_journal(journal_id: str, user_id: str, user_name: str = "User"):
    """
    Full pipeline for processing a submitted journal entry.

    This runs as a background task after journal submission.
    It creates its own database session to avoid lifecycle issues.
    """
    async with SessionLocal() as db:
        try:
            await _process(db, journal_id, user_id, user_name)
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


async def _process(db: AsyncSession, journal_id: str, user_id: str, user_name: str):
    journal = await _get_journal(db, journal_id)
    if not journal:
        logger.error("Journal %s not found", journal_id)
        return

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

    # Step 4: Generate LLM feedback (if OpenRouter key is configured)
    if settings.OPENROUTER_API_KEY:
        logger.info("Generating feedback for journal %s", journal_id)
        result = await llm_service.generate_feedback(
            journal_text=journal.raw_text,
            memories=memories,
        )

        # Step 5: Store feedback
        feedback = JournalFeedback(
            journal_id=journal.id,
            agent_role="reflection_coach",
            response_text=result["response_text"],
            response_json=result.get("response_json"),
            retrieved_memories_json={"memories": memories} if memories else None,
            model_name=result.get("model_name"),
        )
        db.add(feedback)

        journal.status = "processed"
        await db.commit()
        logger.info("Journal %s processed successfully", journal_id)
    else:
        logger.info("OpenRouter API key not configured, skipping feedback generation")
        journal.status = "submitted"
        await db.commit()
