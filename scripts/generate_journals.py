"""
Generate 60+ days of synthetic journal entries using an LLM.

Usage:
  cd backend
  python -m scripts.generate_journals

Or:
  cd scripts
  python generate_journals.py

Requires OPENROUTER_API_KEY in ../backend/.env or as an environment variable.
Outputs: generated_journals.json (importable via Settings → Import in the app)
"""

import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

# ── Config ──────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "x-ai/grok-4-fast"
OUTPUT_FILE = Path(__file__).parent / "generated_journals.json"
NUM_DAYS = 60
MOODS = ["😊", "😌", "😔", "😤", "😰", "🤔", "😴", "🎉", "💪", "❤️"]

# Try loading from backend .env if not set
if not OPENROUTER_API_KEY:
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                OPENROUTER_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found. Set it in environment or backend/.env")
    sys.exit(1)


# ── LLM Helper ──────────────────────────────────────────

async def llm_call(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    """Make a single LLM call via OpenRouter."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.9,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Step 1: Generate Persona ────────────────────────────

async def generate_persona() -> str:
    """Generate a detailed user persona for consistent journal generation."""
    prompt = """Create a detailed persona for a fictional journal writer. Include:

1. **Name & Demographics**: Age, gender, occupation, location
2. **Personality**: Key traits, communication style (sometimes brief, sometimes verbose)
3. **Current Life Situation**: What's going on in their work, relationships, hobbies
4. **Emotional Landscape**: What they struggle with, what brings them joy
5. **Goals & Aspirations**: Both short-term and long-term
6. **Hobbies & Interests**: At least 3-4 specific hobbies
7. **Ongoing Storylines**: 3-4 ongoing situations that will develop over the 60-day period
   (e.g., a work project, a relationship development, a health goal, learning a new skill)

Make this person feel real and multidimensional. They should have good days and bad days,
mundane entries and deep reflections. Their writing style should vary — sometimes a few words,
sometimes multiple sentences.

Output the persona as a detailed character description."""

    print("🧑 Generating user persona...")
    persona = await llm_call(prompt)
    print(f"✅ Persona generated ({len(persona)} chars)")
    return persona


# ── Step 2: Generate Journals in Batches ────────────────

async def generate_batch(
    persona: str,
    start_date: datetime,
    num_days: int,
    previous_summary: str = "",
) -> list[dict]:
    """Generate a batch of journal entries for a range of days."""

    date_range = f"{start_date.strftime('%B %d')} to {(start_date + timedelta(days=num_days-1)).strftime('%B %d, %Y')}"

    prompt = f"""Based on this persona, generate {num_days} days of journal entries from {date_range}.

PERSONA:
{persona}

{"STORY SO FAR (what happened in previous entries):" + chr(10) + previous_summary if previous_summary else ""}

RULES:
- Generate EXACTLY {num_days} entries, one per day, starting from {start_date.strftime('%Y-%m-%d')}
- Some days can have 1-2 entries (morning + evening)
- Vary the LENGTH dramatically: some entries are just 5-15 words, others are 2-4 sentences
- Vary the TOPICS: emotional diary, work updates, hobby progress, business ideas, relationships,
  health/fitness, random observations, gratitude, frustrations, plans, reflections
- Include natural human patterns: Monday blues, weekend excitement, occasional boring days
- Show progression in the ongoing storylines — things should develop and change
- Some entries should reference previous events ("still thinking about...", "update on...")
- Use casual, authentic language — not perfectly polished prose
- Include occasional typos or informal language for realism

OUTPUT FORMAT — respond with ONLY a JSON array, no other text:
[
  {{
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "title": "optional short title or null",
    "content": "the journal entry text",
    "mood": "one of: 😊 😌 😔 😤 😰 🤔 😴 🎉 💪 ❤️"
  }},
  ...
]"""

    system = "You are a creative writing assistant. Output ONLY valid JSON arrays. No markdown, no code fences, no explanation."

    result = await llm_call(prompt, system=system, max_tokens=8000)

    # Clean up the response — strip markdown fences if present
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1] if "\n" in result else result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        entries = json.loads(result)
    except json.JSONDecodeError:
        # Try to find JSON array in the response
        start = result.find("[")
        end = result.rfind("]") + 1
        if start >= 0 and end > start:
            entries = json.loads(result[start:end])
        else:
            print(f"  ⚠️  Failed to parse batch. Raw response:\n{result[:200]}")
            return []

    return entries


async def summarize_entries(persona: str, entries: list[dict]) -> str:
    """Summarize previous entries for context continuity."""
    entries_text = "\n".join(
        f"- {e.get('date', '?')}: {e.get('content', '')[:150]}"
        for e in entries[-15:]  # last 15 entries for context
    )

    prompt = f"""Given this persona and their recent journal entries, write a brief 3-4 sentence summary
of what's been happening in their life. Focus on ongoing storylines and emotional state.

PERSONA (first line): {persona[:200]}

RECENT ENTRIES:
{entries_text}

Write just the summary, nothing else."""

    return await llm_call(prompt, max_tokens=500)


# ── Main ────────────────────────────────────────────────

async def main():
    print(f"📓 Journal Generator — {NUM_DAYS} days of synthetic entries")
    print(f"   Model: {MODEL}")
    print(f"   Output: {OUTPUT_FILE}")
    print()

    # Step 1: Generate persona
    persona = await generate_persona()
    print()

    # Step 2: Generate journals in batches of 10-15 days
    all_entries = []
    start_date = datetime.now(timezone.utc) - timedelta(days=NUM_DAYS)
    previous_summary = ""
    batch_size = 10
    days_generated = 0

    while days_generated < NUM_DAYS:
        remaining = NUM_DAYS - days_generated
        current_batch = min(batch_size, remaining)
        batch_start = start_date + timedelta(days=days_generated)

        print(f"📝 Generating days {days_generated + 1}-{days_generated + current_batch} "
              f"({batch_start.strftime('%b %d')} — {(batch_start + timedelta(days=current_batch - 1)).strftime('%b %d')})...")

        entries = await generate_batch(persona, batch_start, current_batch, previous_summary)

        if entries:
            all_entries.extend(entries)
            print(f"   ✅ Got {len(entries)} entries")

            # Summarize for next batch's context
            if days_generated + current_batch < NUM_DAYS:
                previous_summary = await summarize_entries(persona, all_entries)
        else:
            print(f"   ❌ Batch failed, retrying...")
            continue

        days_generated += current_batch

    # Step 3: Convert to import format
    print(f"\n📦 Converting {len(all_entries)} entries to import format...")

    journals = []
    for entry in all_entries:
        date_str = entry.get("date", "")
        time_str = entry.get("time", f"{random.randint(7, 22):02d}:{random.randint(0, 59):02d}")

        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc) - timedelta(days=random.randint(0, NUM_DAYS))

        content = entry.get("content", "").strip()
        if not content:
            continue

        mood = entry.get("mood")
        if mood not in MOODS:
            mood = random.choice(MOODS)

        journals.append({
            "title": entry.get("title"),
            "content": content,
            "mood": mood,
            "source": "import",
            "created_at": dt.isoformat(),
        })

    # Sort by date
    journals.sort(key=lambda j: j["created_at"])

    output = {"journals": journals, "total": len(journals)}
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Done! Generated {len(journals)} journal entries over {NUM_DAYS} days")
    print(f"   File: {OUTPUT_FILE}")
    print(f"\n   To import: Settings → Import Data → Choose '{OUTPUT_FILE.name}'")


if __name__ == "__main__":
    asyncio.run(main())
