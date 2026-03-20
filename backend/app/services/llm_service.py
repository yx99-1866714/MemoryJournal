"""
LLM service using OpenRouter API.

Generates agent feedback for journal entries using retrieved memories as context.
The model is configurable via the LLM_MODEL environment variable.
"""
import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 60.0

# Default Reflection Coach agent config
DEFAULT_AGENT = {
    "name": "Reflection Coach",
    "role": "reflection_coach",
    "purpose": "Help the user notice patterns and make sense of entries over time",
    "tone": "warm, curious, nonjudgmental",
}

SYSTEM_PROMPT_TEMPLATE = """You are the user's {name}.
Your role is: {purpose}
Your tone should be: {tone}

Use the user's previous memories only to provide continuity and personalized insight.
Do not diagnose. Do not exaggerate certainty.
If the user appears in crisis, switch to safe supportive guidance.

Respond with a JSON object containing these sections:
{{
  "today_summary": "Brief summary of what the user shared today",
  "pattern_connection": "Connections to past entries or recurring themes (use memories if available)",
  "supportive_observation": "A warm, nonjudgmental observation",
  "next_step": "A practical, gentle suggestion",
  "reflection_question": "A thoughtful question to encourage deeper reflection"
}}

IMPORTANT: Return ONLY the JSON object, no markdown fencing or extra text."""


def _build_prompt(
    journal_text: str,
    memories: list[dict[str, Any]],
    agent_config: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build the chat messages for the LLM call."""
    agent = agent_config or DEFAULT_AGENT

    system = SYSTEM_PROMPT_TEMPLATE.format(
        name=agent.get("name", "Reflection Coach"),
        purpose=agent.get("purpose", DEFAULT_AGENT["purpose"]),
        tone=agent.get("tone", DEFAULT_AGENT["tone"]),
    )

    # Build context from memories
    memory_context = ""
    if memories:
        memory_lines = []
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", mem.get("text", str(mem)))
            memory_lines.append(f"[Memory {i}] {content}")
        memory_context = "\n\n--- Previous memories ---\n" + "\n".join(memory_lines) + "\n--- End memories ---\n"

    user_message = f"""Here is the user's journal entry:

---
{journal_text}
---
{memory_context}
Please provide your feedback as the JSON object described."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


async def generate_feedback(
    journal_text: str,
    memories: list[dict[str, Any]] | None = None,
    agent_config: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Call OpenRouter to generate agent feedback for a journal entry.

    Returns a dict with:
      - response_text: the full text response
      - response_json: parsed structured sections (or None if parsing fails)
      - model_name: the model used
    """
    messages = _build_prompt(journal_text, memories or [], agent_config)
    model = settings.LLM_MODEL

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://memoryjournal.app",
        "X-Title": "Memory Journal",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Extract the response text
    response_text = data["choices"][0]["message"]["content"]
    logger.info("LLM response received, model=%s, length=%d", model, len(response_text))

    # Try to parse structured JSON
    response_json = None
    try:
        # Strip markdown fencing if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        response_json = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Could not parse LLM response as JSON, storing as plain text")

    return {
        "response_text": response_text,
        "response_json": response_json,
        "model_name": model,
    }
