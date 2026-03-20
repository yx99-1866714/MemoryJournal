"""
EverMemOS API client.

Handles memory submission, status polling, and memory search/retrieval.
All EverMemOS API keys stay server-side — never exposed to the extension.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.EVERMEMOS_API_URL.rstrip("/")
TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.EVERMEMOS_API_KEY}",
        "Content-Type": "application/json",
    }


def _log_request(method: str, url: str, body: Any = None, params: Any = None):
    """Log outgoing request details when VERBOSE is enabled."""
    if not settings.VERBOSE:
        return
    logger.info("──── EverMemOS REQUEST ────")
    logger.info("  %s %s", method, url)
    if params:
        logger.info("  Params: %s", json.dumps(params, default=str))
    if body:
        logger.info("  Body: %s", json.dumps(body, default=str, indent=2))
    logger.info("───────────────────────────")


def _log_response(resp: httpx.Response):
    """Log response details when VERBOSE is enabled."""
    if not settings.VERBOSE:
        return
    logger.info("──── EverMemOS RESPONSE ────")
    logger.info("  Status: %d", resp.status_code)
    try:
        logger.info("  Body: %s", json.dumps(resp.json(), default=str, indent=2))
    except Exception:
        logger.info("  Body: %s", resp.text[:500])
    logger.info("────────────────────────────")


async def submit_memory(
    content: str,
    user_id: str,
    journal_id: str,
    user_name: str = "User",
) -> dict[str, Any]:
    """
    Send a journal entry to EverMemOS for memory extraction.

    Returns the response dict containing request_id and status.
    """
    url = f"{BASE_URL}/api/v0/memories"
    payload = {
        "message_id": f"journal_{journal_id}",
        "create_time": datetime.now(timezone.utc).isoformat(),
        "sender": user_id,
        "sender_name": user_name,
        "role": "user",
        "content": content,
        "group_id": f"{user_id}_journal",
        "group_name": f"{user_name} Journal Stream",
        "flush": True,
    }

    _log_request("POST", url, body=payload)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=_headers())
        _log_response(resp)
        resp.raise_for_status()
        data = resp.json()
        logger.info("EverMemOS submit_memory response: %s", data)
        return data


async def get_request_status(request_id: str) -> dict[str, Any]:
    """
    Poll the processing status of a previously submitted memory request.
    """
    url = f"{BASE_URL}/api/v0/status/request"
    params = {"request_id": request_id}

    _log_request("GET", url, params=params)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
        _log_response(resp)
        resp.raise_for_status()
        return resp.json()


async def search_memories(
    query: str,
    user_id: str,
    max_results: int = 8,
    memory_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Search EverMemOS for relevant memories given a query string.

    Returns a list of memory objects.
    """
    url = f"{BASE_URL}/api/v0/memories/search"
    params: dict[str, Any] = {
        "query": query,
        "user_id": user_id,
        "top_k": max_results,
    }
    if memory_types:
        params["memory_types"] = ",".join(memory_types)

    _log_request("GET", url, params=params)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
        _log_response(resp)
        resp.raise_for_status()
        data = resp.json()

        # Debug: log the response keys at each level
        if settings.VERBOSE:
            logger.info("EverMemOS search response top-level keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            inner_data = data.get("data") if isinstance(data, dict) else None
            if isinstance(inner_data, dict):
                logger.info("EverMemOS search response data keys: %s", list(inner_data.keys()))

        # Walk the response structure to find memories
        # EverMemOS wraps under "result" (confirmed: top-level keys are ['status', 'message', 'result'])
        memories = []
        if isinstance(data, dict):
            inner = data.get("result") or data.get("data") or {}
            if not isinstance(inner, dict):
                inner = {}

            # Extract both memories and profiles
            mem_list = []
            profile_list = []

            if isinstance(data.get("memories"), list):
                mem_list = data["memories"]
            elif isinstance(inner.get("memories"), list):
                mem_list = inner["memories"]
            elif isinstance(data.get("results"), list):
                mem_list = data["results"]

            # Profiles are separate in EverMemOS responses
            if isinstance(inner.get("profiles"), list):
                profile_list = inner["profiles"]
            elif isinstance(data.get("profiles"), list):
                profile_list = data["profiles"]

            memories = mem_list + profile_list

            # Also include pending_messages
            pending = []
            if isinstance(inner.get("pending_messages"), list):
                pending = inner["pending_messages"]
            elif isinstance(data.get("pending_messages"), list):
                pending = data["pending_messages"]
            if pending:
                logger.info("EverMemOS search has %d pending messages, including them", len(pending))
                memories = memories + pending

            if settings.VERBOSE:
                logger.info("EverMemOS search breakdown: %d memories, %d profiles, %d pending",
                            len(mem_list), len(profile_list), len(pending))

        logger.info("EverMemOS search returned %d items total", len(memories))
        return memories


async def delete_memories(
    memory_ids: list[str] | None = None,
    user_id: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """
    Delete memories from EverMemOS by filter criteria.

    Can filter by memory_id/event_id, user_id, and/or group_id.
    Returns the delete result with count of deleted items.
    """
    url = f"{BASE_URL}/api/v0/memories"
    body: dict[str, Any] = {}
    if memory_ids and len(memory_ids) == 1:
        body["event_id"] = memory_ids[0]
    if user_id:
        body["user_id"] = user_id
    if group_id:
        body["group_id"] = group_id

    _log_request("DELETE", url, body=body)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.request("DELETE", url, json=body, headers=_headers())
        _log_response(resp)
        resp.raise_for_status()
        data = resp.json()
        # EverMemOS reports affected count in message, not in result.count
        message = data.get("message", "")
        logger.info("EverMemOS delete_memories: %s", message)
        return data

