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


async def generate_title(journal_text: str) -> str:
    """Generate a short title for a journal entry using the LLM."""
    model = settings.LLM_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                "Generate a short, evocative title (3-7 words) for the following journal entry. "
                "Return ONLY the title text, nothing else. No quotes, no punctuation at the end."
            ),
        },
        {"role": "user", "content": journal_text[:1000]},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 30,
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
    title = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
    logger.info("Generated title: %s", title)
    return title


async def generate_tags(journal_text: str, existing_tags: list[str]) -> list[str]:
    """Generate 1-5 topic tags for a journal entry, reusing existing tags when possible."""
    model = settings.LLM_MODEL
    existing_str = ", ".join(f'"{t}"' for t in existing_tags) if existing_tags else "(none yet)"
    messages = [
        {
            "role": "system",
            "content": (
                "You are a journal categorization assistant. Generate 1-5 short topic tags for the following journal entry.\n\n"
                "Rules:\n"
                "- Tags should be broad categories like 'emotional diary', 'work', 'health & fitness', 'home improvement', 'travel', 'finances', 'relationships', 'self-care', 'career', etc.\n"
                "- Each tag should be 1-3 words, all lowercase\n"
                "- Reuse existing tags when they fit. Here are the user's existing tags: " + existing_str + "\n"
                "- Only create a new tag if none of the existing ones are a good fit\n"
                "- Return ONLY a JSON array of tag strings, no markdown fencing\n"
                "- Example: [\"emotional diary\", \"relationships\", \"self-care\"]\n"
            ),
        },
        {"role": "user", "content": journal_text[:1500]},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 100,
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
    raw = data["choices"][0]["message"]["content"].strip()
    # Strip markdown fencing if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    tags = json.loads(raw)
    if not isinstance(tags, list):
        tags = []
    # Normalize: lowercase, strip, deduplicate, limit 5
    seen = set()
    clean = []
    for t in tags:
        t = str(t).strip().lower()[:100]
        if t and t not in seen:
            seen.add(t)
            clean.append(t)
        if len(clean) >= 5:
            break
    logger.info("Generated tags: %s", clean)
    return clean

async def extract_goals_tasks(journal_text: str) -> dict[str, list]:
    """
    Extract goals and tasks from a journal entry.

    Returns: {"goals": [{...}], "tasks": [{...}]}
    """
    from datetime import date as _date

    today_str = _date.today().isoformat()  # e.g. "2026-03-21"
    model = settings.LLM_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                f"Today's date is {today_str}.\n\n"
                "Analyze the following journal entry and extract any goals or actionable tasks the user mentions.\n\n"
                "Rules:\n"
                "- Goals are bigger objectives like 'exercise more', 'learn Spanish', 'save money'\n"
                "- Tasks are specific actionable items like 'call doctor', 'buy groceries', 'finish report by Friday'\n"
                "- Only extract items the user actually mentions or implies they want to do\n"
                "- Do NOT invent goals/tasks that aren't in the text\n"
                "- If there are no goals or tasks, return empty arrays\n"
                "- For each goal/task, determine if it is 'one_time' or 'recurring'\n"
                "- If recurring, set recurrence_frequency to one of: 'daily', 'weekly', 'monthly', 'yearly'\n"
                "- If one-time, set recurrence_frequency to null\n"
                "- If a deadline or due date is mentioned or implied (e.g. 'by Friday', 'next week', 'before March 30'), "
                "set due_date to the ISO date string (YYYY-MM-DD). If no deadline, set due_date to null\n\n"
                "Return ONLY valid JSON in this format, no markdown fencing:\n"
                '{"goals": [{"title": "short title", "description": "brief context", "recurrence": "one_time", "recurrence_frequency": null, "due_date": null}], '
                '"tasks": [{"title": "specific action item", "recurrence": "one_time", "recurrence_frequency": null, "due_date": null}]}'
            ),
        },
        {"role": "user", "content": journal_text[:2000]},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 500,
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

    raw = data["choices"][0]["message"]["content"].strip()
    # Strip markdown fencing if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse goals/tasks JSON: %s", raw[:200])
        return {"goals": [], "tasks": []}

    goals = result.get("goals", []) if isinstance(result.get("goals"), list) else []
    tasks = result.get("tasks", []) if isinstance(result.get("tasks"), list) else []
    logger.info("Extracted %d goals and %d tasks", len(goals), len(tasks))
    return {"goals": goals, "tasks": tasks}


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


CHAT_SYSTEM_TEMPLATE = """You are the user's {name}.
Your role is: {purpose}
Your tone should be: {tone}

The user is having a follow-up conversation about their journal entry.
Use the journal text and previous memories for context and continuity.
Do not diagnose. Do not exaggerate certainty.
If the user appears in crisis, switch to safe supportive guidance.

Respond naturally in a conversational way. Keep responses concise but thoughtful."""


async def generate_chat_response(
    thread_messages: list,
    journal_text: str = "",
    memories: list[dict[str, Any]] | None = None,
    agent_config: dict[str, str] | None = None,
    tz_offset_minutes: int | None = None,
) -> dict[str, Any]:
    """
    Generate a follow-up chat response using the thread history as context.

    Returns a dict with:
      - response_text: the assistant's reply
      - model_name: the model used
    """
    from datetime import datetime, timezone, timedelta

    agent = agent_config or DEFAULT_AGENT
    model = settings.LLM_MODEL

    system = CHAT_SYSTEM_TEMPLATE.format(
        name=agent.get("name", "Reflection Coach"),
        purpose=agent.get("purpose", DEFAULT_AGENT["purpose"]),
        tone=agent.get("tone", DEFAULT_AGENT["tone"]),
    )

    # Inject user's local date/time at the TOP of the prompt so it takes priority
    if tz_offset_minutes is not None:
        local_now = datetime.now(timezone.utc) + timedelta(minutes=-tz_offset_minutes)
    else:
        local_now = datetime.now(timezone.utc)
    day_name = local_now.strftime("%A")  # e.g. "Saturday"
    date_str = local_now.strftime("%B %d, %Y")  # e.g. "March 21, 2026"
    time_str = local_now.strftime("%I:%M %p")  # e.g. "09:53 PM"
    date_preamble = (
        f"IMPORTANT: The user's current local date and time is {day_name}, {date_str}, {time_str}. "
        f"Always use this as the reference for 'today', 'this weekend', 'tomorrow', etc. "
        f"Note: Any timestamps in memories or journal metadata may be in UTC and should NOT be used to determine the user's local date.\n\n"
    )
    logger.info("Agent date preamble: tz_offset=%s, computed=%s %s %s", tz_offset_minutes, day_name, date_str, time_str)
    system = date_preamble + system

    # Add journal context
    if journal_text:
        system += f"\n\n--- Journal Entry ---\n{journal_text}\n--- End Journal ---"

    # Add memory context
    if memories:
        memory_lines = []
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", mem.get("text", str(mem)))
            memory_lines.append(f"[Memory {i}] {content}")
        system += "\n\n--- Previous Memories ---\n" + "\n".join(memory_lines) + "\n--- End Memories ---"

    # Build messages from thread history
    messages = [{"role": "system", "content": system}]
    for msg in thread_messages:
        role = msg.role if hasattr(msg, "role") else msg.get("role", "user")
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
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

    response_text = data["choices"][0]["message"]["content"]
    logger.info("LLM chat response received, model=%s, length=%d", model, len(response_text))

    return {
        "response_text": response_text,
        "model_name": model,
    }


# ── Goal Secretary (tool-use) ────────────────────────

GOAL_SECRETARY_SYSTEM_TEMPLATE = """You are the user's Goal Secretary.
Your role is: Help the user manage their goals and tasks — create new goals, break them into tasks, track progress, and adjust plans.
Your tone should be: {tone}

You have the ability to CREATE, UPDATE, and DELETE goals and tasks. When the user asks you to manage their goals/tasks, you MUST include the appropriate actions in your response.

IMPORTANT: You MUST respond in valid JSON with this exact structure:
{{
  "reply": "Your conversational response to the user",
  "actions": [
    // Optional array of actions to execute. Omit if no actions needed.
  ]
}}

Available action types:
- {{"type": "create_goal", "title": "Goal title", "description": "Optional description"}}
- {{"type": "create_task", "goal_title": "Parent goal title", "title": "Task title", "due_at": "ISO date for one-time tasks", "recurrence_frequency": "daily|weekly for recurring tasks"}}
- {{"type": "update_goal", "goal_title": "Existing goal title", "status": "active|completed|paused|abandoned"}}
- {{"type": "update_task", "task_title": "Existing task title", "status": "open|completed|dismissed"}}
- {{"type": "delete_goal", "goal_title": "Goal title to delete"}}
- {{"type": "delete_task", "task_title": "Task title to delete"}}

TASK TYPES — there are two kinds of tasks:
1. ONE-TIME tasks: have a "due_at" deadline date (ISO format). No recurrence_frequency.
2. RECURRING tasks: have a "recurrence_frequency" of "daily" or "weekly". Do NOT set "due_at" for recurring tasks.
   - Daily tasks auto-reset to incomplete at the start of each day.
   - Weekly tasks auto-reset to incomplete every Monday.

When creating tasks, decide based on context whether a task should be one-time or recurring:
- "Exercise every day" → recurring (daily)
- "Clean bedroom weekly" → recurring (weekly)
- "Buy a new shelf by Friday" → one-time with due_at
- "Finish report" → one-time (due_at optional)

Rules:
- ALWAYS respond with valid JSON. No markdown, no code fences, just raw JSON.
- Use "goal_title" to reference existing goals, "task_title" to reference existing tasks.
- When creating tasks, link them to a goal using "goal_title" (must match an existing or newly created goal title).
- If the user is just chatting and not asking to change goals/tasks, respond with just {{"reply": "your message"}} and no actions.
- Keep replies concise but helpful.
- When breaking down goals into tasks, create the tasks with clear, actionable titles.
- You can create a goal and its tasks in a single response.

{goals_context}"""


async def generate_goal_secretary_response(
    thread_messages: list,
    goals_context: str,
    journal_text: str = "",
    memories: list[dict[str, Any]] | None = None,
    agent_config: dict[str, str] | None = None,
    tz_offset_minutes: int | None = None,
) -> dict[str, Any]:
    """
    Generate a Goal Secretary response with optional structured actions.

    Returns a dict with:
      - response_text: the conversational reply
      - actions: list of action dicts (may be empty)
      - model_name: the model used
    """
    from datetime import datetime, timezone, timedelta

    agent = agent_config or {}
    model = settings.LLM_MODEL

    # Build goals context section
    goals_section = ""
    if goals_context:
        goals_section = f"\n\n--- Current Goals & Tasks ---\n{goals_context}\n--- End Goals & Tasks ---"

    system = GOAL_SECRETARY_SYSTEM_TEMPLATE.format(
        tone=agent.get("tone", "organized, proactive, and encouraging"),
        goals_context=goals_section,
    )

    # Inject user's local date/time
    if tz_offset_minutes is not None:
        local_now = datetime.now(timezone.utc) + timedelta(minutes=-tz_offset_minutes)
    else:
        local_now = datetime.now(timezone.utc)
    day_name = local_now.strftime("%A")
    date_str = local_now.strftime("%B %d, %Y")
    time_str = local_now.strftime("%I:%M %p")
    date_preamble = (
        f"IMPORTANT: The user's current local date and time is {day_name}, {date_str}, {time_str}. "
        f"Always use this as the reference for 'today', 'this weekend', 'tomorrow', etc.\n\n"
    )
    system = date_preamble + system

    # Add journal context
    if journal_text:
        system += f"\n\n--- Journal Entry ---\n{journal_text}\n--- End Journal ---"

    # Add memory context
    if memories:
        memory_lines = []
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", mem.get("text", str(mem)))
            memory_lines.append(f"[Memory {i}] {content}")
        system += "\n\n--- Previous Memories ---\n" + "\n".join(memory_lines) + "\n--- End Memories ---"

    # Build messages
    messages = [{"role": "system", "content": system}]
    for msg in thread_messages:
        role = msg.role if hasattr(msg, "role") else msg.get("role", "user")
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,  # slightly lower for more reliable JSON
        "max_tokens": 1200,
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

    raw_text = data["choices"][0]["message"]["content"]
    logger.info("Goal Secretary raw response, model=%s, length=%d", model, len(raw_text))

    # Parse the JSON response
    response_text, actions = _parse_goal_secretary_response(raw_text)

    return {
        "response_text": response_text,
        "actions": actions,
        "model_name": model,
    }


def _parse_goal_secretary_response(raw: str) -> tuple[str, list[dict]]:
    """
    Parse the LLM's JSON response into (reply_text, actions).
    Falls back gracefully if the response isn't valid JSON.
    """
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove ```json ... ``` wrapping
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
        reply = parsed.get("reply", "")
        actions = parsed.get("actions", [])
        if not isinstance(actions, list):
            actions = []
        return reply, actions
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Goal Secretary response was not valid JSON, using raw text")
        return raw.strip(), []


CHECKIN_SYSTEM_TEMPLATE = """You are the user's {name}.
Your role is: {purpose}
Your tone should be: {tone}

The user just submitted a journal entry. Your job is to send ONE short, warm check-in message
that acknowledges what they wrote about and gently invites them to continue the conversation with you.

Rules:
- Keep it to 1-3 sentences, conversational and natural
- Reference something specific from their journal entry to show you read it
- End with an open-ended question or gentle invitation to chat
- Match your specific agent personality and tone
- Do NOT summarize the whole entry, just pick one thing that stands out
- Do NOT use headers, bullet points, or structured formatting
- Do NOT start with "Hey" or "Hi" every time — vary your openings"""


async def generate_checkin_message(
    journal_text: str,
    memories: list[dict[str, Any]] | None = None,
    agent_config: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Generate a proactive check-in message from an agent after the user submits a journal.

    Returns a dict with:
      - response_text: the check-in message
      - model_name: the model used
    """
    agent = agent_config or DEFAULT_AGENT
    model = settings.LLM_MODEL

    system = CHECKIN_SYSTEM_TEMPLATE.format(
        name=agent.get("name", "Reflection Coach"),
        purpose=agent.get("purpose", DEFAULT_AGENT["purpose"]),
        tone=agent.get("tone", DEFAULT_AGENT["tone"]),
    )

    # Add memory context
    if memories:
        memory_lines = []
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", mem.get("text", str(mem)))
            memory_lines.append(f"[Memory {i}] {content}")
        system += "\n\n--- Previous Memories ---\n" + "\n".join(memory_lines) + "\n--- End Memories ---"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Here is the user's journal entry:\n\n{journal_text}"},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 200,
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

    response_text = data["choices"][0]["message"]["content"]
    logger.info("Agent check-in generated for %s, length=%d", agent.get("name"), len(response_text))

    return {
        "response_text": response_text,
        "model_name": model,
    }


EMOTIONAL_ANALYSIS_PROMPT = """Analyze the user's recent emotional state based on the following journals and chat messages.

Classify the urgency into one of three levels:
- "critical": The user is going through something traumatic (breakup, loss, crisis, severe anxiety/depression, suicidal thoughts). They need frequent emotional support.
- "elevated": The user is experiencing mild-to-moderate stress, sadness, frustration, or is clearly not feeling great. They could benefit from a daily check-in.
- "normal": The user seems generally fine — neutral, positive, or just going about their routine.

Return ONLY valid JSON in this exact format, no markdown fencing:
{"urgency": "critical|elevated|normal", "summary": "1-2 sentence summary of their emotional state"}"""


async def analyze_emotional_state(
    recent_journals: list[str],
    recent_chat_excerpts: list[str],
    goals_context: str = "",
) -> dict[str, str]:
    """
    Analyze user's emotional state from recent journals and chats.
    Returns {"urgency": "critical|elevated|normal", "summary": "..."}
    """
    model = settings.LLM_MODEL

    context_parts = []
    for i, j in enumerate(recent_journals, 1):
        context_parts.append(f"[Journal {i}] {j[:500]}")
    for i, c in enumerate(recent_chat_excerpts, 1):
        context_parts.append(f"[Chat {i}] {c[:300]}")
    if goals_context:
        context_parts.append(f"[Goals/Tasks Context] {goals_context}")

    user_content = "\n\n".join(context_parts) if context_parts else "No recent activity."

    messages = [
        {"role": "system", "content": EMOTIONAL_ANALYSIS_PROMPT},
        {"role": "user", "content": user_content},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 150,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://memoryjournal.app",
        "X-Title": "Memory Journal",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        raw = data["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = json.loads(raw)
        urgency = result.get("urgency", "normal")
        if urgency not in ("critical", "elevated", "normal"):
            urgency = "normal"
        return {"urgency": urgency, "summary": result.get("summary", "")}
    except Exception as e:
        logger.warning("Emotional state analysis failed: %s", e)
        return {"urgency": "normal", "summary": "Unable to determine"}


PROACTIVE_CHECKIN_TEMPLATE = """You are the user's {name}.
Your role is: {purpose}
Your tone should be: {tone}

You are sending a proactive check-in message to the user. This is NOT in response to a journal entry —
you are reaching out on your own initiative based on what you know about the user.

{role_specific_instructions}

Context about the user's recent activity:
{context}

Rules:
- Keep it to 2-4 sentences, conversational and natural
- Reference something specific from the context to show you're paying attention
- End with an open-ended question or gentle invitation to chat
- Match your specific agent personality and tone
- Do NOT use headers, bullet points, or structured formatting
- Do NOT start with "Hey" or "Hi" every time — vary your openings
- Be genuine and helpful, not generic"""


async def generate_proactive_checkin(
    agent_config: dict[str, str],
    context: str,
    role_specific_instructions: str = "",
) -> dict[str, Any]:
    """
    Generate a proactive check-in message from an agent.
    """
    agent = agent_config or DEFAULT_AGENT
    model = settings.LLM_MODEL

    system = PROACTIVE_CHECKIN_TEMPLATE.format(
        name=agent.get("name", "Reflection Coach"),
        purpose=agent.get("purpose", DEFAULT_AGENT["purpose"]),
        tone=agent.get("tone", DEFAULT_AGENT["tone"]),
        role_specific_instructions=role_specific_instructions,
        context=context,
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Please send your proactive check-in message now."},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 250,
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

    response_text = data["choices"][0]["message"]["content"]
    logger.info("Proactive check-in generated for %s, length=%d", agent.get("name"), len(response_text))

    return {
        "response_text": response_text,
        "model_name": model,
    }

