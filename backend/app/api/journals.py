import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db import get_db
from app.models.journal import Journal
from app.models.journal_feedback import JournalFeedback
from app.models.tag import Tag, journal_tags
from app.schemas.feedback import FeedbackListResponse, FeedbackResponse, ProcessingStatusResponse
from app.schemas.journal import JournalCreate, JournalListResponse, JournalResponse, JournalUpdate, TagListResponse, TagResponse
from app.services import journal_service
from app.services.process_journal import process_journal

router = APIRouter(prefix="/journals", tags=["journals"])


async def _journal_to_response(j, db: AsyncSession) -> JournalResponse:
    # Fetch tags for this journal
    tag_result = await db.execute(
        select(Tag).join(journal_tags).where(journal_tags.c.journal_id == j.id)
    )
    tags = [
        TagResponse(id=str(t.id), name=t.name)
        for t in tag_result.scalars().all()
    ]
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
        tags=tags,
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
            selected_agent_id=body.selected_agent_id,
        )

    return await _journal_to_response(journal, db)


@router.get("/export")
async def export_journals(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Export all journals as a JSON download."""
    from fastapi.responses import JSONResponse

    journals, _ = await journal_service.get_journals(
        db, user_id=uuid.UUID(user_id), limit=10000, offset=0,
    )
    data = [
        {
            "id": str(j.id),
            "title": j.title,
            "content": j.raw_text,
            "status": j.status,
            "word_count": j.word_count,
            "mood": j.mood_label,
            "source": j.source_surface,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "submitted_at": j.submitted_at.isoformat() if j.submitted_at else None,
        }
        for j in journals
    ]
    return JSONResponse(
        content={"journals": data, "total": len(data)},
        headers={"Content-Disposition": "attachment; filename=MemoryJournal_export.json"},
    )


@router.post("/import")
async def import_journals(
    body: dict,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Import journals from exported JSON. Skips duplicates (matching content)."""
    from datetime import datetime, timezone
    from hashlib import sha256
    from app.models.journal import Journal as JournalModel
    from app.services.process_journal import process_journal

    uid = uuid.UUID(user_id)
    entries = body.get("journals", [])
    if not entries:
        return {"imported": 0, "skipped": 0, "total": 0}

    # Build a set of content hashes for existing journals to detect duplicates
    existing, _ = await journal_service.get_journals(db, uid, limit=10000, offset=0)
    existing_hashes = {
        sha256((j.raw_text or "").strip().encode()).hexdigest()
        for j in existing
    }

    imported = 0
    skipped = 0

    for entry in entries:
        content = entry.get("content", "").strip()
        if not content:
            skipped += 1
            continue

        content_hash = sha256(content.encode()).hexdigest()
        if content_hash in existing_hashes:
            skipped += 1
            continue

        # Parse created_at from export if available
        created_at = None
        if entry.get("created_at"):
            try:
                created_at = datetime.fromisoformat(entry["created_at"])
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                created_at = None

        journal = JournalModel(
            user_id=uid,
            title=entry.get("title"),
            raw_text=content,
            status="submitted",
            word_count=len(content.split()),
            mood_label=entry.get("mood"),
            source_surface=entry.get("source", "import"),
            created_at=created_at or datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(journal)
        await db.flush()
        await db.refresh(journal)

        # Queue background processing (EverMemOS + goals/tasks extraction)
        background_tasks.add_task(
            process_journal,
            journal_id=str(journal.id),
            user_id=user_id,
        )

        existing_hashes.add(content_hash)
        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped, "total": len(entries)}


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
    responses = [await _journal_to_response(j, db) for j in journals]
    return JournalListResponse(
        journals=responses,
        total=total,
    )


@router.get("/dates", response_model=list[int])
async def get_journal_dates(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    tz_offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return day-of-month numbers that have journal entries for a given year/month."""
    days = await journal_service.get_journal_dates_for_month(
        db, user_id=uuid.UUID(user_id), year=year, month=month,
        tz_offset_minutes=tz_offset,
    )
    return days


@router.get("/by-date", response_model=JournalListResponse)
async def get_journals_by_date(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    tz_offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all journals for a specific date."""
    journals = await journal_service.get_journals_by_date(
        db, user_id=uuid.UUID(user_id), year=year, month=month, day=day,
        tz_offset_minutes=tz_offset,
    )
    responses = [await _journal_to_response(j, db) for j in journals]
    return JournalListResponse(
        journals=responses,
        total=len(journals),
    )


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all tags for the current user with journal counts."""
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(
            Tag.id,
            Tag.name,
            func.count(journal_tags.c.journal_id).label("journal_count"),
        )
        .outerjoin(journal_tags, Tag.id == journal_tags.c.tag_id)
        .where(Tag.user_id == uid)
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(journal_tags.c.journal_id).desc())
    )
    tags = [
        TagResponse(id=str(row.id), name=row.name, journal_count=row.journal_count)
        for row in result.all()
    ]
    return TagListResponse(tags=tags)


@router.get("/by-tag/{tag_id}", response_model=JournalListResponse)
async def get_journals_by_tag(
    tag_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all journals for a specific tag."""
    uid = uuid.UUID(user_id)
    tid = uuid.UUID(tag_id)
    result = await db.execute(
        select(Journal)
        .join(journal_tags, Journal.id == journal_tags.c.journal_id)
        .where(
            journal_tags.c.tag_id == tid,
            Journal.user_id == uid,
        )
        .order_by(Journal.created_at.desc())
    )
    journals = list(result.scalars().all())
    responses = [await _journal_to_response(j, db) for j in journals]
    return JournalListResponse(journals=responses, total=len(responses))


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    return await _journal_to_response(journal, db)


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
        
    was_processed = journal.status in ("processed", "submitted")
    content_changed = body.content is not None

    updated = await journal_service.update_journal(
        db,
        journal,
        content=body.content,
        title=body.title,
        submit=body.submit,
        mood_label=body.mood_label,
    )

    # Trigger processing if a draft is being submitted OR a processed journal is edited
    should_process = (body.submit and updated.status == "submitted") or (was_processed and content_changed)

    if should_process:
        updated.status = "submitted"
        await db.commit()
        background_tasks.add_task(
            process_journal,
            journal_id=str(updated.id),
            user_id=user_id,
        )

    return await _journal_to_response(updated, db)


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

