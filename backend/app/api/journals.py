import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db import get_db
from app.models.journal_feedback import JournalFeedback
from app.schemas.feedback import FeedbackListResponse, FeedbackResponse, ProcessingStatusResponse
from app.schemas.journal import JournalCreate, JournalListResponse, JournalResponse, JournalUpdate
from app.services import journal_service
from app.services.process_journal import process_journal

router = APIRouter(prefix="/journals", tags=["journals"])


def _journal_to_response(j) -> JournalResponse:
    return JournalResponse(
        id=str(j.id),
        user_id=str(j.user_id),
        title=j.title,
        raw_text=j.raw_text,
        status=j.status,
        word_count=j.word_count,
        mood_label=j.mood_label,
        source_surface=j.source_surface,
        created_at=j.created_at,
        updated_at=j.updated_at,
        submitted_at=j.submitted_at,
    )


@router.post("/", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    body: JournalCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.create_journal(
        db,
        user_id=uuid.UUID(user_id),
        content=body.content,
        title=body.title,
        submit=body.submit,
        source_surface=body.source_surface,
        mood_label=body.mood_label,
    )

    # Trigger background processing for submitted journals
    if body.submit:
        background_tasks.add_task(
            process_journal,
            journal_id=str(journal.id),
            user_id=user_id,
        )

    return _journal_to_response(journal)


@router.get("/", response_model=JournalListResponse)
async def list_journals(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    journals, total = await journal_service.get_journals(
        db, user_id=uuid.UUID(user_id), limit=limit, offset=offset
    )
    return JournalListResponse(
        journals=[_journal_to_response(j) for j in journals],
        total=total,
    )


@router.get("/dates", response_model=list[int])
async def get_journal_dates(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return day-of-month numbers that have journal entries for a given year/month."""
    days = await journal_service.get_journal_dates_for_month(
        db, user_id=uuid.UUID(user_id), year=year, month=month
    )
    return days


@router.get("/by-date", response_model=JournalListResponse)
async def get_journals_by_date(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all journals for a specific date."""
    journals = await journal_service.get_journals_by_date(
        db, user_id=uuid.UUID(user_id), year=year, month=month, day=day
    )
    return JournalListResponse(
        journals=[_journal_to_response(j) for j in journals],
        total=len(journals),
    )


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    return _journal_to_response(journal)


@router.get("/{journal_id}/feedback", response_model=FeedbackListResponse)
async def get_journal_feedback(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all AI feedback for a journal entry."""
    # Verify journal belongs to user
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")

    result = await db.execute(
        select(JournalFeedback)
        .where(JournalFeedback.journal_id == uuid.UUID(journal_id))
        .order_by(JournalFeedback.created_at.desc())
    )
    feedbacks = result.scalars().all()

    return FeedbackListResponse(
        feedback=[
            FeedbackResponse(
                id=str(f.id),
                journal_id=str(f.journal_id),
                agent_role=f.agent_role,
                response_text=f.response_text,
                response_json=f.response_json,
                model_name=f.model_name,
                created_at=f.created_at,
            )
            for f in feedbacks
        ]
    )


@router.get("/{journal_id}/status", response_model=ProcessingStatusResponse)
async def get_journal_status(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the processing status of a journal entry."""
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")

    # Check if feedback exists
    result = await db.execute(
        select(JournalFeedback.id)
        .where(JournalFeedback.journal_id == uuid.UUID(journal_id))
        .limit(1)
    )
    has_feedback = result.scalar_one_or_none() is not None

    return ProcessingStatusResponse(
        journal_id=str(journal.id),
        status=journal.status,
        evermemos_status=journal.evermemos_status,
        has_feedback=has_feedback,
    )


@router.patch("/{journal_id}", response_model=JournalResponse)
async def update_journal(
    journal_id: str,
    body: JournalUpdate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    updated = await journal_service.update_journal(
        db,
        journal,
        content=body.content,
        title=body.title,
        submit=body.submit,
        mood_label=body.mood_label,
    )

    # Trigger processing if a draft is being submitted
    if body.submit and updated.status == "submitted":
        background_tasks.add_task(
            process_journal,
            journal_id=str(updated.id),
            user_id=user_id,
        )

    return _journal_to_response(updated)


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal(
    journal_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    await journal_service.delete_journal(db, journal)

    # Clean up associated memories from EverMemOS in the background
    background_tasks.add_task(
        _delete_evermemos_memories,
        journal_id=journal_id,
        user_id=user_id,
        journal_text=journal.raw_text,
    )


async def _delete_evermemos_memories(journal_id: str, user_id: str, journal_text: str):
    """Background task to search for and delete journal-associated memories from EverMemOS."""
    import logging
    from app.config import settings
    from app.services import evermemos

    logger = logging.getLogger(__name__)

    if not settings.EVERMEMOS_API_KEY:
        return

    try:
        # Search using the journal content (which EverMemOS actually indexed)
        memories = await evermemos.search_memories(
            query=journal_text[:500],
            user_id=user_id,
            max_results=50,
        )

        if not memories:
            logger.info("No EverMemOS memories found for journal %s", journal_id)
            return

        # Try to match memories by message_id in original_data or ori_event_id_list
        target_message_id = f"journal_{journal_id}"
        matched_ids = []
        for mem in memories:
            mem_id = mem.get("id")
            if not mem_id:
                continue

            # Check original_data.messages[].extend.message_id
            for orig in (mem.get("original_data") or []):
                for msg in (orig.get("messages") or []):
                    extend = msg.get("extend") or {}
                    if extend.get("message_id") == target_message_id:
                        matched_ids.append(mem_id)
                        # Also grab parent_id (memcell) for deletion
                        parent = mem.get("parent_id")
                        if parent and parent not in matched_ids:
                            matched_ids.append(parent)
                        break

            # Check ori_event_id_list
            if mem_id not in matched_ids:
                event_ids = mem.get("ori_event_id_list") or []
                if target_message_id in event_ids:
                    matched_ids.append(mem_id)
                    parent = mem.get("parent_id")
                    if parent and parent not in matched_ids:
                        matched_ids.append(parent)

        # Deduplicate
        matched_ids = list(dict.fromkeys(matched_ids))

        if matched_ids:
            logger.info("Attempting to delete %d EverMemOS items for journal %s: %s", len(matched_ids), journal_id, matched_ids)
            for mem_id in matched_ids:
                try:
                    await evermemos.delete_memories(memory_ids=[mem_id], user_id=user_id)
                except Exception as e:
                    logger.warning("Failed to delete EverMemOS memory %s: %s", mem_id, e)
            logger.info("Finished deleting EverMemOS memories for journal %s", journal_id)
        else:
            logger.info(
                "No exact message_id match for journal %s in %d search results. "
                "Memory types found: %s",
                journal_id,
                len(memories),
                [m.get("memory_type", "unknown") for m in memories],
            )
    except Exception as e:
        logger.warning("Failed to clean up EverMemOS memories for journal %s: %s", journal_id, e)


