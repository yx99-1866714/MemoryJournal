import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user_id(authorization: str = Header(...)) -> str:
    """Extract and validate the JWT from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    token = authorization[len("Bearer "):]
    user_id = auth_service.decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user_id


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await auth_service.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await auth_service.register_user(db, body.email, body.name, body.password)
    token = auth_service.create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_service.create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=str(user.id), email=user.email, name=user.name)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user_id: str = Depends(get_current_user_id)):
    token = auth_service.create_access_token(user_id)
    return TokenResponse(access_token=token)


@router.delete("/account", status_code=204)
async def delete_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete the user account and all associated data."""
    from sqlalchemy import delete
    from app.models.journal import Journal
    from app.models.journal_feedback import JournalFeedback
    from app.models.goal import Goal
    from app.models.task import Task
    from app.models.agent import Agent
    from app.models.agent_thread import AgentThread, AgentMessage
    from app.models.user import User

    uid = uuid.UUID(user_id)

    # Delete in dependency order: messages → threads → feedback → journals → tasks → goals → agents → user
    # 1. Agent messages (via threads)
    threads = await db.execute(select(AgentThread.id).where(AgentThread.user_id == uid))
    thread_ids = [t[0] for t in threads.all()]
    if thread_ids:
        await db.execute(delete(AgentMessage).where(AgentMessage.thread_id.in_(thread_ids)))

    # 2. Agent threads
    await db.execute(delete(AgentThread).where(AgentThread.user_id == uid))

    # 3. Journal feedback
    journals = await db.execute(select(Journal.id).where(Journal.user_id == uid))
    journal_ids = [j[0] for j in journals.all()]
    if journal_ids:
        await db.execute(delete(JournalFeedback).where(JournalFeedback.journal_id.in_(journal_ids)))

    # 4. Journals
    await db.execute(delete(Journal).where(Journal.user_id == uid))

    # 5. Tasks
    await db.execute(delete(Task).where(Task.user_id == uid))

    # 6. Goals
    await db.execute(delete(Goal).where(Goal.user_id == uid))

    # 7. Custom agents
    await db.execute(delete(Agent).where(Agent.user_id == uid))

    # 8. User
    await db.execute(delete(User).where(User.id == uid))

    await db.commit()
