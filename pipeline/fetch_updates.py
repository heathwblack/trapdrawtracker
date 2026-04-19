"""Use Claude + web search to fetch news updates for each monitoring item.

For each item in docs/items.json, asks Claude to search the web for developments
on the topic between the episode date and today. Writes updates back to the
same item as an `updates` list ({summary, sources:[{title, url, date}]}).

Idempotent per item via `updates_fetched_at`. Pass --force to refresh all.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from anthropic import Anthropic

from pipeline.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ITEMS_PATH

SYSTEM_PROMPT = """You help track news updates for items covered on the Trap Draw podcast. Given a specific topic and when it was discussed on the podcast, your job is to:

1. Use the web_search tool (up to 2 searches) to find news developments on the topic between the episode date and today.
2. Return a concise update via the record_updates tool.

Be selective: only include meaningful developments — a new court filing, a confirmed outcome, a notable follow-up story. Skip rehashes of the original news and unrelated results. If nothing substantive has happened since the episode, return an empty updates array with a brief explanation.

For each update, include specific source URLs and publication dates where possible."""


UPDATES_TOOL = {
    "name": "record_updates",
    "description": "Record news updates on the topic since the episode aired.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-3 sentence synthesis of what's happened on this topic since the episode. If nothing meaningful, say so briefly.",
            },
            "updates": {
                "type": "array",
                "description": "Discrete news items published after the episode date. Empty if nothing found.",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "date": {"type": "string", "description": "Publication date in YYYY-MM-DD if known, else empty."},
                        "source": {"type": "string", "description": "Publication name (e.g. 'NYT', 'ESPN')."},
                        "url": {"type": "string"},
                        "summary": {"type": "string", "description": "1-2 sentences on what this update adds."},
                    },
                    "required": ["headline", "url", "summary"],
                },
            },
        },
        "required": ["summary", "updates"],
    },
}

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 2,
}


def fetch_updates_for_item(client: Anthropic, item: dict, today_iso: str) -> dict:
    user_msg = (
        f"Topic: {item['title']}\n"
        f"Topic tag: {item['topic']}\n"
        f"Episode aired: {item['episode_date']}\n"
        f"Today: {today_iso}\n"
        f"The hosts' take at the time: {item['pov_summary']}\n\n"
        f"Search for news developments on this topic published between "
        f"{item['episode_date']} and {today_iso}, then call record_updates."
    )

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[WEB_SEARCH_TOOL, UPDATES_TOOL],
        messages=[{"role": "user", "content": user_msg}],
    )

    # Walk the response for a record_updates tool_use block
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_updates":
            return block.input

    # Fallback: Claude didn't call the tool (unlikely with our prompt)
    return {"summary": "No structured update produced.", "updates": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch updates for every item.")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0 = all).")
    parser.add_argument("--episode", type=int, default=0, help="Only process items for this episode number.")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY not set.")

    store = json.loads(ITEMS_PATH.read_text())
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    today = date.today().isoformat()

    targets = [i for i in store["items"] if args.force or "updates_fetched_at" not in i]
    if args.episode:
        targets = [i for i in targets if i["episode"] == args.episode]
    if args.limit:
        targets = targets[: args.limit]

    print(f"Fetching updates for {len(targets)} items (total {len(store['items'])})")
    for n, item in enumerate(targets, 1):
        print(f"  [{n}/{len(targets)}] ep{item['episode']}  {item['title']}")
        try:
            result = fetch_updates_for_item(client, item, today)
        except Exception as e:  # noqa: BLE001
            print(f"        ERROR: {e}")
            continue
        item["updates_summary"] = result.get("summary", "")
        item["updates"] = result.get("updates", [])
        item["updates_fetched_at"] = today
        ITEMS_PATH.write_text(json.dumps(store, indent=2))
        n_updates = len(item["updates"])
        print(f"        {n_updates} update(s) — {item['updates_summary'][:100]}")


if __name__ == "__main__":
    main()
