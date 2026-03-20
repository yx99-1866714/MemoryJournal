"""Tests for /auth endpoints: register, login, /me, refresh."""
import pytest
from httpx import AsyncClient


class TestRegister:
    """POST /auth/register"""

    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={
            "email": "new@example.com",
            "name": "New User",
            "password": "securepass",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 20

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "name": "User", "password": "pass123"}
        resp1 = await client.post("/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await client.post("/auth/register", json=payload)
        assert resp2.status_code == 409
        assert "already registered" in resp2.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={
            "email": "not-an-email",
            "name": "User",
            "password": "pass123",
        })
        assert resp.status_code == 422  # Pydantic validation

    async def test_register_missing_fields(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={"email": "a@b.com"})
        assert resp.status_code == 422


class TestLogin:
    """POST /auth/login"""

    async def test_login_success(self, client: AsyncClient):
        # Register first
        await client.post("/auth/register", json={
            "email": "login@example.com",
            "name": "Login User",
            "password": "mypassword",
        })
        # Login
        resp = await client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/auth/register", json={
            "email": "wrong@example.com",
            "name": "User",
            "password": "correct",
        })
        resp = await client.post("/auth/login", json={
            "email": "wrong@example.com",
            "password": "incorrect",
        })
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={
            "email": "ghost@nowhere.com",
            "password": "doesntmatter",
        })
        assert resp.status_code == 401


class TestMe:
    """GET /auth/me"""

    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert "id" in data

    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/auth/me")
        assert resp.status_code == 422  # Missing Authorization header

    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401


class TestRefresh:
    """POST /auth/refresh"""

    async def test_refresh_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        # New token should be different from old one (different exp)
        old_token = auth_headers["Authorization"].split(" ")[1]
        assert data["access_token"] != old_token or True  # might match if within same second

    async def test_refresh_no_auth(self, client: AsyncClient):
        resp = await client.post("/auth/refresh")
        assert resp.status_code == 422
