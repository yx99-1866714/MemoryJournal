"""Tests for /journals endpoints: CRUD, dates, by-date."""
import pytest
from httpx import AsyncClient


async def _create_journal(client: AsyncClient, headers: dict, **overrides) -> dict:
    """Helper to create a journal and return the response data."""
    payload = {
        "content": overrides.get("content", "Today was a great day."),
        "title": overrides.get("title", "My Journal"),
        "submit": overrides.get("submit", True),
        "source_surface": overrides.get("source_surface", "fullpage"),
        "mood_label": overrides.get("mood_label", "😊"),
    }
    resp = await client.post("/journals/", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateJournal:
    """POST /journals/"""

    async def test_create_submitted(self, client: AsyncClient, auth_headers: dict):
        data = await _create_journal(client, auth_headers, submit=True)
        assert data["status"] == "submitted"
        assert data["title"] == "My Journal"
        assert data["raw_text"] == "Today was a great day."
        assert data["word_count"] == 5
        assert data["mood_label"] == "😊"
        assert data["source_surface"] == "fullpage"
        assert data["submitted_at"] is not None
        assert "id" in data

    async def test_create_draft(self, client: AsyncClient, auth_headers: dict):
        data = await _create_journal(client, auth_headers, submit=False)
        assert data["status"] == "draft"
        assert data["submitted_at"] is None

    async def test_create_no_auth(self, client: AsyncClient):
        resp = await client.post("/journals/", json={"content": "hello"})
        assert resp.status_code == 422

    async def test_create_missing_content(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/journals/", json={"title": "No content"}, headers=auth_headers)
        assert resp.status_code == 422


class TestListJournals:
    """GET /journals/"""

    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/journals/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["journals"] == []
        assert data["total"] == 0

    async def test_list_with_entries(self, client: AsyncClient, auth_headers: dict):
        await _create_journal(client, auth_headers, title="Entry 1")
        await _create_journal(client, auth_headers, title="Entry 2")
        await _create_journal(client, auth_headers, title="Entry 3")

        resp = await client.get("/journals/", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 3
        assert len(data["journals"]) == 3

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        for i in range(5):
            await _create_journal(client, auth_headers, title=f"Entry {i}")

        resp = await client.get("/journals/?limit=2&offset=0", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 5
        assert len(data["journals"]) == 2

        resp2 = await client.get("/journals/?limit=2&offset=2", headers=auth_headers)
        data2 = resp2.json()
        assert data2["total"] == 5
        assert len(data2["journals"]) == 2

        # IDs should be different between pages
        page1_ids = {j["id"] for j in data["journals"]}
        page2_ids = {j["id"] for j in data2["journals"]}
        assert page1_ids.isdisjoint(page2_ids)


class TestGetJournal:
    """GET /journals/{id}"""

    async def test_get_existing(self, client: AsyncClient, auth_headers: dict):
        created = await _create_journal(client, auth_headers)
        resp = await client.get(f"/journals/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent(self, client: AsyncClient, auth_headers: dict):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/journals/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_other_users_journal(self, client: AsyncClient):
        """A user should not see another user's journal."""
        # User 1 creates a journal
        resp1 = await client.post("/auth/register", json={
            "email": "user1@test.com", "name": "User1", "password": "pass123"
        })
        headers1 = {"Authorization": f"Bearer {resp1.json()['access_token']}"}
        journal = await _create_journal(client, headers1)

        # User 2 tries to read it
        resp2 = await client.post("/auth/register", json={
            "email": "user2@test.com", "name": "User2", "password": "pass123"
        })
        headers2 = {"Authorization": f"Bearer {resp2.json()['access_token']}"}
        resp = await client.get(f"/journals/{journal['id']}", headers=headers2)
        assert resp.status_code == 404  # Should not be visible


class TestUpdateJournal:
    """PATCH /journals/{id}"""

    async def test_update_title(self, client: AsyncClient, auth_headers: dict):
        created = await _create_journal(client, auth_headers)
        resp = await client.patch(
            f"/journals/{created['id']}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["raw_text"] == created["raw_text"]  # unchanged

    async def test_update_content(self, client: AsyncClient, auth_headers: dict):
        created = await _create_journal(client, auth_headers)
        resp = await client.patch(
            f"/journals/{created['id']}",
            json={"content": "Totally new content with more words now"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["raw_text"] == "Totally new content with more words now"
        assert resp.json()["word_count"] == 7

    async def test_update_submit_draft(self, client: AsyncClient, auth_headers: dict):
        created = await _create_journal(client, auth_headers, submit=False)
        assert created["status"] == "draft"

        resp = await client.patch(
            f"/journals/{created['id']}",
            json={"submit": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"
        assert resp.json()["submitted_at"] is not None

    async def test_update_nonexistent(self, client: AsyncClient, auth_headers: dict):
        import uuid
        resp = await client.patch(
            f"/journals/{uuid.uuid4()}",
            json={"title": "Nope"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestDeleteJournal:
    """DELETE /journals/{id}"""

    async def test_delete_existing(self, client: AsyncClient, auth_headers: dict):
        created = await _create_journal(client, auth_headers)
        resp = await client.delete(f"/journals/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = await client.get(f"/journals/{created['id']}", headers=auth_headers)
        assert resp2.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient, auth_headers: dict):
        import uuid
        resp = await client.delete(f"/journals/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestJournalDates:
    """GET /journals/dates"""

    async def test_dates_empty_month(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/journals/dates?year=2020&month=1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_dates_current_month(self, client: AsyncClient, auth_headers: dict):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        await _create_journal(client, auth_headers, title="Today's entry")
        resp = await client.get(
            f"/journals/dates?year={now.year}&month={now.month}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        days = resp.json()
        assert now.day in days

    async def test_dates_invalid_month(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/journals/dates?year=2026&month=13", headers=auth_headers)
        assert resp.status_code == 422


class TestJournalsByDate:
    """GET /journals/by-date"""

    async def test_by_date_with_entries(self, client: AsyncClient, auth_headers: dict):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        await _create_journal(client, auth_headers, title="Morning entry")
        await _create_journal(client, auth_headers, title="Evening entry")

        resp = await client.get(
            f"/journals/by-date?year={now.year}&month={now.month}&day={now.day}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["journals"]) == 2

    async def test_by_date_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/journals/by-date?year=2020&month=1&day=1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_by_date_no_auth(self, client: AsyncClient):
        resp = await client.get("/journals/by-date?year=2026&month=3&day=19")
        assert resp.status_code == 422
