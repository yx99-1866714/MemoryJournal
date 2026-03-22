"""Tests for /goals endpoints: reminders, summary, CRUD."""
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.task import Task


# ── Helpers ───────────────────────────────────────────

async def _get_user_id(client: AsyncClient, headers: dict) -> str:
    """Get the user id from the auth headers by calling /auth/me."""
    resp = await client.get("/auth/me", headers=headers)
    return resp.json()["id"]


async def _create_goal(db: AsyncSession, user_id: str, **overrides) -> Goal:
    """Create a goal directly via the shared DB session."""
    goal = Goal(
        user_id=uuid.UUID(user_id),
        title=overrides.get("title", "Test Goal"),
        description=overrides.get("description", "A test goal"),
        status=overrides.get("status", "active"),
        recurrence=overrides.get("recurrence", "one_time"),
        recurrence_frequency=overrides.get("recurrence_frequency"),
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def _create_task(db: AsyncSession, user_id: str, **overrides) -> Task:
    """Create a task directly via the shared DB session."""
    task = Task(
        user_id=uuid.UUID(user_id),
        goal_id=uuid.UUID(overrides["goal_id"]) if overrides.get("goal_id") else None,
        title=overrides.get("title", "Test Task"),
        status=overrides.get("status", "open"),
        due_at=overrides.get("due_at"),
        last_reminded_at=overrides.get("last_reminded_at"),
        recurrence=overrides.get("recurrence", "one_time"),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# ── Reminders Endpoint ───────────────────────────────

class TestReminders:
    """GET /goals/reminders"""

    async def test_reminders_empty(self, client: AsyncClient, auth_headers: dict):
        """No tasks → no reminders."""
        resp = await client.get("/goals/reminders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reminders"] == []
        assert data["count"] == 0

    async def test_reminders_overdue_task(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """A task due in the past should be returned as 'overdue'."""
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=5)
        await _create_task(db_session, uid, title="Overdue task", due_at=past)

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 1
        assert data["reminders"][0]["urgency"] == "overdue"
        assert data["reminders"][0]["title"] == "Overdue task"

    async def test_reminders_due_today(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """A task due in 12 hours should be returned as 'today'."""
        uid = await _get_user_id(client, auth_headers)
        soon = datetime.utcnow() + timedelta(hours=12)
        await _create_task(db_session, uid, title="Today task", due_at=soon)

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 1
        assert data["reminders"][0]["urgency"] == "today"

    async def test_reminders_due_tomorrow(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """A task due in 36 hours should be returned as 'tomorrow'."""
        uid = await _get_user_id(client, auth_headers)
        later = datetime.utcnow() + timedelta(hours=36)
        await _create_task(db_session, uid, title="Tomorrow task", due_at=later)

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 1
        assert data["reminders"][0]["urgency"] == "tomorrow"

    async def test_reminders_skip_recently_reminded(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """Tasks reminded within 12 hours should be skipped."""
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=2)
        recently = datetime.utcnow() - timedelta(hours=1)
        await _create_task(
            db_session, uid,
            title="Already reminded", due_at=past, last_reminded_at=recently,
        )

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 0

    async def test_reminders_skip_completed_tasks(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """Completed tasks should not generate reminders."""
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=5)
        await _create_task(
            db_session, uid,
            title="Done task", due_at=past, status="completed",
        )

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 0

    async def test_reminders_skip_far_future(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """Tasks due more than 48h out should not generate reminders."""
        uid = await _get_user_id(client, auth_headers)
        far = datetime.utcnow() + timedelta(hours=72)
        await _create_task(db_session, uid, title="Far away", due_at=far)

        resp = await client.get("/goals/reminders", headers=auth_headers)
        data = resp.json()
        assert data["count"] == 0

    async def test_reminders_updates_last_reminded_at(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """After fetching reminders, last_reminded_at should be set (so next call returns 0)."""
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=2)
        await _create_task(db_session, uid, title="Remind me", due_at=past)

        # First call — should return 1 reminder
        resp1 = await client.get("/goals/reminders", headers=auth_headers)
        assert resp1.json()["count"] == 1

        # Second call immediately — should return 0 (already reminded)
        resp2 = await client.get("/goals/reminders", headers=auth_headers)
        assert resp2.json()["count"] == 0

    async def test_reminders_no_auth(self, client: AsyncClient):
        """Unauthenticated requests should fail."""
        resp = await client.get("/goals/reminders")
        assert resp.status_code == 422


# ── Summary Endpoint ──────────────────────────────────

class TestGoalsSummary:
    """GET /goals/summary"""

    async def test_summary_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/goals/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_goals"] == 0
        assert data["open_tasks"] == 0
        assert data["overdue_tasks"] == 0
        assert data["due_today_tasks"] == 0

    async def test_summary_with_overdue_tasks(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=5)
        await _create_task(db_session, uid, title="Overdue", due_at=past)

        resp = await client.get("/goals/summary", headers=auth_headers)
        data = resp.json()
        assert data["overdue_tasks"] == 1
        assert data["open_tasks"] == 1

    async def test_summary_with_due_today_tasks(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        uid = await _get_user_id(client, auth_headers)
        soon = datetime.utcnow() + timedelta(hours=6)
        await _create_task(db_session, uid, title="Today", due_at=soon)

        resp = await client.get("/goals/summary", headers=auth_headers)
        data = resp.json()
        assert data["due_today_tasks"] == 1
        assert data["overdue_tasks"] == 0

    async def test_summary_counts_only_open(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """Completed tasks should not count toward overdue."""
        uid = await _get_user_id(client, auth_headers)
        past = datetime.utcnow() - timedelta(hours=5)
        await _create_task(
            db_session, uid,
            title="Done", due_at=past, status="completed",
        )

        resp = await client.get("/goals/summary", headers=auth_headers)
        data = resp.json()
        assert data["overdue_tasks"] == 0
        assert data["open_tasks"] == 0


# ── Goal Update Endpoint ─────────────────────────────

class TestGoalUpdate:
    """PATCH /goals/{goal_id}"""

    async def test_update_title(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        uid = await _get_user_id(client, auth_headers)
        goal = await _create_goal(db_session, uid, title="Old Title")
        resp = await client.patch(
            f"/goals/{goal.id}",
            json={"title": "New Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_update_recurrence(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        uid = await _get_user_id(client, auth_headers)
        goal = await _create_goal(db_session, uid)
        resp = await client.patch(
            f"/goals/{goal.id}",
            json={"recurrence": "recurring", "recurrence_frequency": "weekly"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recurrence"] == "recurring"
        assert data["recurrence_frequency"] == "weekly"

    async def test_update_invalid_recurrence(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        uid = await _get_user_id(client, auth_headers)
        goal = await _create_goal(db_session, uid)
        resp = await client.patch(
            f"/goals/{goal.id}",
            json={"recurrence": "invalid_value"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Should stay unchanged since "invalid_value" is not a valid option
        assert resp.json()["recurrence"] == "one_time"

    async def test_update_nonexistent(self, client: AsyncClient, auth_headers: dict):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/goals/{fake_id}",
            json={"title": "Nope"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
