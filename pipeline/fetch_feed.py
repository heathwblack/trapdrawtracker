"""Parse the Trap Draw RSS feed and return 2026 Chop Session episodes."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

import feedparser

from pipeline.config import CHOP_TITLE_RE, FEED_URL, TARGET_YEAR


@dataclass
class Episode:
    number: int
    title: str
    date: str
    mp3_url: str
    spotify_id: Optional[str]
    duration_sec: Optional[int]
    description: str


def _spotify_id_from_links(entry) -> Optional[str]:
    for link in getattr(entry, "links", []):
        href = link.get("href", "")
        m = re.search(r"open\.spotify\.com/episode/([A-Za-z0-9]+)", href)
        if m:
            return m.group(1)
    return None


def _parse_duration(value) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, int):
        return value
    parts = str(value).split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    if len(parts) == 1:
        return parts[0]
    return None


def fetch_episodes() -> list[Episode]:
    feed = feedparser.parse(FEED_URL)
    episodes: list[Episode] = []
    for entry in feed.entries:
        title = entry.get("title", "")
        m = re.match(CHOP_TITLE_RE, title)
        if not m:
            continue
        published = entry.get("published_parsed")
        if not published or published.tm_year != TARGET_YEAR:
            continue
        mp3_url = ""
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("audio"):
                mp3_url = enc.get("href", "")
                break
        if not mp3_url:
            continue
        episodes.append(
            Episode(
                number=int(m.group(1)),
                title=title,
                date=datetime(*published[:6]).strftime("%Y-%m-%d"),
                mp3_url=mp3_url,
                spotify_id=_spotify_id_from_links(entry),
                duration_sec=_parse_duration(entry.get("itunes_duration")),
                description=entry.get("summary", ""),
            )
        )
    episodes.sort(key=lambda e: e.number)
    return episodes


def main() -> None:
    eps = fetch_episodes()
    print(f"Found {len(eps)} Chop Session episodes in {TARGET_YEAR}:")
    for e in eps:
        print(f"  {e.number}  {e.date}  {e.title}")
    print()
    print(json.dumps([asdict(e) for e in eps], indent=2))


if __name__ == "__main__":
    main()
