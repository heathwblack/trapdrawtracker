"""Extract monitoring items from transcripts using Claude tool-use."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from anthropic import Anthropic

from pipeline.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ITEMS_PATH
from pipeline.fetch_feed import Episode, fetch_episodes
from pipeline.transcribe import transcript_path

SYSTEM_PROMPT = """You analyze transcripts of "Chop Session" episodes from the Trap Draw podcast (No Laying Up). The hosts — Big, Soly, DJ Pie, TC, Neil, Randy, and rotating guests — run through a mix of golf news, sports stories, world/culture happenings, and running bits.

Chop Sessions frequently include an explicit segment called the "monitoring list" where the hosts review ongoing stories they're watching. Your job is to extract ALL monitoring items from the episode — both the literal "monitoring list" segment if present, AND any other substantive topic the hosts discuss with a distinct point of view elsewhere in the episode.

Think of it as: "What are the things Trap Draw is watching this week, and what do they think about them?"

INCLUDE items when:
- They appear on the explicit monitoring list segment (highest priority)
- The hosts spend real time on a topic (not a passing mention)
- They express an opinion, reaction, or take — not just factual recap
- It's a story, situation, development, or ongoing saga worth tracking
- Recurring bits like "Things That Are Sick" nominations count if they're substantive

EXCLUDE:
- Personal anecdotes, what they did this weekend, family stuff
- Pure banter, inside jokes, bits that don't anchor to a topic
- Sponsor reads and ad breaks (Rhoback, Whoop, Nest, etc.)
- Episode housekeeping, greetings, introductions of guests
- Throwaway lines or one-sentence asides
- "What I'm cooking/reading/watching" style personal media picks, unless they tie to a broader ongoing story

For each monitoring item, return:
- title: 5–10 words, snappy and specific (e.g. "Mt Everest insurance fraud scheme", not "Mountaineering news")
- category: one of golf, sports, world-news, culture, business, other
- timestamp_sec: integer seconds into the episode where the discussion begins
- pov_summary: 2–3 sentences in the hosts' voice capturing their actual take — what they think, not a neutral summary
- status: forward-looking status from the hosts' perspective ("ongoing investigation, hosts skeptical", "waiting on next court date", "appears resolved but they're not sure", etc.)
- quote: a short direct excerpt (1–2 sentences, under 200 chars) from the transcript that illustrates their POV

Aim for 4–10 items per episode. Be selective — a tight tracker is more useful than a comprehensive one."""


TOOL = {
    "name": "record_monitoring_items",
    "description": "Record the monitoring items extracted from this episode's transcript.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["golf", "sports", "world-news", "culture", "business", "other"],
                        },
                        "timestamp_sec": {"type": "integer"},
                        "pov_summary": {"type": "string"},
                        "status": {"type": "string"},
                        "quote": {"type": "string"},
                    },
                    "required": ["title", "category", "timestamp_sec", "pov_summary", "status", "quote"],
                },
            }
        },
        "required": ["items"],
    },
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60]


def _format_timestamp(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _flatten_transcript(transcript_json: dict) -> str:
    lines: list[str] = []
    for seg in transcript_json.get("transcription", []):
        start_ms = seg.get("offsets", {}).get("from", 0)
        secs = start_ms // 1000
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{_format_timestamp(secs)}] {text}")
    return "\n".join(lines)


def extract_items(ep: Episode) -> list[dict]:
    tpath = transcript_path(ep.number)
    if not tpath.exists():
        raise FileNotFoundError(f"Transcript missing for episode {ep.number}: {tpath}")
    transcript_json = json.loads(tpath.read_text())
    flat = _flatten_transcript(transcript_json)
    if not flat:
        raise ValueError(f"Transcript for episode {ep.number} is empty")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": TOOL["name"]},
        messages=[
            {
                "role": "user",
                "content": f"Episode {ep.number} ({ep.date}) transcript follows. Extract monitoring items.\n\n{flat}",
            }
        ],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == TOOL["name"]:
            return block.input["items"]
    raise RuntimeError(f"Claude did not invoke {TOOL['name']} for episode {ep.number}")


def load_existing() -> dict:
    if ITEMS_PATH.exists():
        return json.loads(ITEMS_PATH.read_text())
    return {"episodes": [], "items": []}


def save(store: dict) -> None:
    ITEMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ITEMS_PATH.write_text(json.dumps(store, indent=2))


def upsert_episode(store: dict, ep: Episode, extracted: list[dict]) -> None:
    store["episodes"] = [e for e in store["episodes"] if e["number"] != ep.number]
    store["episodes"].append({
        "number": ep.number,
        "title": ep.title,
        "date": ep.date,
        "spotify_id": ep.spotify_id,
        "duration_sec": ep.duration_sec,
    })
    store["episodes"].sort(key=lambda e: e["number"])

    store["items"] = [i for i in store["items"] if i["episode"] != ep.number]
    for raw in extracted:
        ts = int(raw["timestamp_sec"])
        store["items"].append({
            "id": f"{ep.number}-{_slug(raw['title'])}",
            "episode": ep.number,
            "episode_date": ep.date,
            "title": raw["title"],
            "category": raw["category"],
            "timestamp_sec": ts,
            "timestamp_display": _format_timestamp(ts),
            "pov_summary": raw["pov_summary"],
            "status": raw["status"],
            "quote": raw["quote"],
        })
    store["items"].sort(key=lambda i: (i["episode"], i["timestamp_sec"]))


def main() -> None:
    if not ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
    store = load_existing()
    for ep in fetch_episodes():
        print(f"  extract  {ep.number}  {ep.title}")
        items = extract_items(ep)
        upsert_episode(store, ep, items)
        save(store)
    print(f"Wrote {len(store['items'])} items across {len(store['episodes'])} episodes to {ITEMS_PATH}")


if __name__ == "__main__":
    main()
