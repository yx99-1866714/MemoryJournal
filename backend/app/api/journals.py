import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db import get_db
from app.schemas.journal import JournalCreate, JournalListResponse, JournalResponse, JournalUpdate
from app.services import journal_service

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


@router.patch("/{journal_id}", response_model=JournalResponse)
async def update_journal(
    journal_id: str,
    body: JournalUpdate,
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
    return _journal_to_response(updated)


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await journal_service.get_journal(db, uuid.UUID(journal_id), uuid.UUID(user_id))
    if journal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal not found")
    await journal_service.delete_journal(db, journal)
