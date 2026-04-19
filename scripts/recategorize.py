"""One-off: re-categorize all items in docs/items.json using the new taxonomy.

Drops the legacy `topic` field. Preserves everything else (including any
`updates` / `updates_summary` / `updates_fetched_at` already fetched).

Uses a single Claude tool-use call to batch-classify all items.
"""
from __future__ import annotations

import json
import sys

from anthropic import Anthropic

from pipeline.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ITEMS_PATH
from pipeline.extract import CATEGORIES

PROMPT = """You are re-categorizing items from the Trap Draw podcast tracker using a tightened taxonomy. The legacy category field was a loose enum of 6 values; it's being replaced with a 14-value enum that covers the real story types.

Categories:
- golf — any golf (Tour, players, architecture, LIV, majors, rules, sponsorships)
- nfl — any NFL (games, draft, playoffs, coaching, free agency, gossip, specific teams)
- nba — NBA
- mlb — MLB / baseball (incl. World Baseball Classic)
- college-hoops — college basketball, March Madness, conference stuff
- other-sports — NHL, tennis, F1, soccer, Olympics, college football, everything else in sports
- air-travel — airlines, airports, flying, aviation
- food-and-drink — restaurants, CPG brands, grocery, dining, recipes
- crime-and-politics — crimes, politicians, government actions, scandals, indictments, Epstein
- world-news — international affairs, geopolitics, weather, natural disasters, animal/nature stories
- media-and-entertainment — TV, movies, books, music, podcasts, celebrity drama
- tech-and-business — tech co's, AI, crypto, business deals, corporate fiascos, antitrust
- show-bits — recurring pod segments ("Things That Are Sick", "Monitoring List", host-personal recurring jokes)
- other — only if truly nothing above fits

For each item below, pick exactly one category. Return via the record_recategorization tool."""


def main() -> None:
    if not ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY not set.")

    store = json.loads(ITEMS_PATH.read_text())
    items = store["items"]

    rows = []
    for i in items:
        rows.append({
            "id": i["id"],
            "title": i["title"],
            "legacy_category": i.get("category"),
            "legacy_topic": i.get("topic"),
            "pov": i["pov_summary"][:220],
        })

    tool = {
        "name": "record_recategorization",
        "description": "Record the new category for each item.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {"type": "string", "enum": CATEGORIES},
                        },
                        "required": ["id", "category"],
                    },
                }
            },
            "required": ["assignments"],
        },
    }

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": json.dumps(rows, indent=2)}],
    )

    assignments = None
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            assignments = block.input["assignments"]
            break
    if assignments is None:
        sys.exit("Claude did not produce assignments.")

    by_id = {a["id"]: a["category"] for a in assignments}
    missing = [i["id"] for i in items if i["id"] not in by_id]
    if missing:
        print(f"WARNING: {len(missing)} items missing from assignments: {missing[:5]}")

    for i in items:
        if i["id"] in by_id:
            i["category"] = by_id[i["id"]]
        i.pop("topic", None)

    ITEMS_PATH.write_text(json.dumps(store, indent=2))

    from collections import Counter
    counts = Counter(i["category"] for i in items)
    print(f"Re-categorized {len(items)} items. Distribution:")
    for cat, n in counts.most_common():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
