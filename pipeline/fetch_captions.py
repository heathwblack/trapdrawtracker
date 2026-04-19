"""Fetch YouTube auto-captions for 2026 Chop Session episodes via yt-dlp.

This replaces the mp3-download + whisper transcription path. yt-dlp is used to
(1) enumerate Chop Session videos on the No Laying Up Podcast channel and
(2) download English auto-captions in YouTube's json3 format, which we convert
to the same transcript shape the extract step already expects.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from pipeline.config import CHOP_TITLE_RE, TARGET_YEAR, TRANSCRIPT_DIR
from pipeline.fetch_feed import fetch_episodes

CHANNEL_URL = "https://www.youtube.com/@NoLayingUpPodcast/videos"


def _list_channel_videos() -> list[dict]:
    """Return [{id, title}, ...] for every video on the NLU channel."""
    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "%(id)s\t%(title)s", CHANNEL_URL],
        check=True, capture_output=True, text=True,
    )
    videos = []
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        vid, title = line.split("\t", 1)
        videos.append({"id": vid.strip(), "title": title.strip()})
    return videos


def _match_video_for_episode(videos: list[dict], ep_number: int) -> Optional[str]:
    pat = re.compile(rf"Trap Draw,?\s*Ep\.?\s*{ep_number}\b", re.IGNORECASE)
    for v in videos:
        if pat.search(v["title"]):
            return v["id"]
    return None


def _json3_to_transcript(json3: dict) -> dict:
    """Convert YouTube json3 caption format to our whisper-compatible shape."""
    segments = []
    for ev in json3.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        segments.append({
            "offsets": {"from": int(start_ms), "to": int(start_ms + dur_ms)},
            "text": text,
        })
    return {"transcription": segments}


def _download_captions(video_id: str) -> dict:
    """Run yt-dlp to grab English auto-captions as json3 and parse them."""
    with tempfile.TemporaryDirectory() as tmp:
        out_template = str(Path(tmp) / "cap.%(ext)s")
        subprocess.run(
            ["yt-dlp", "--skip-download",
             "--write-auto-subs", "--sub-lang", "en",
             "--sub-format", "json3",
             "-o", out_template,
             f"https://www.youtube.com/watch?v={video_id}"],
            check=True, capture_output=True, text=True,
        )
        vtt_files = list(Path(tmp).glob("cap*.json3"))
        if not vtt_files:
            raise RuntimeError(f"No json3 captions produced for {video_id}")
        return json.loads(vtt_files[0].read_text())


def transcript_path(number: int) -> Path:
    return TRANSCRIPT_DIR / f"{number}.json"


def fetch_episode_transcript(ep_number: int, videos: list[dict]) -> Path:
    out = transcript_path(ep_number)
    if out.exists() and out.stat().st_size > 0:
        print(f"  skip  {ep_number}  (already have transcript)")
        return out
    video_id = _match_video_for_episode(videos, ep_number)
    if not video_id:
        raise RuntimeError(f"No YouTube video found for episode {ep_number}")
    print(f"  get   {ep_number}  youtube:{video_id}")
    json3 = _download_captions(video_id)
    transcript = _json3_to_transcript(json3)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(transcript, indent=2))
    segs = len(transcript["transcription"])
    print(f"        {segs} segments")
    return out


def main() -> None:
    videos = _list_channel_videos()
    print(f"Enumerated {len(videos)} videos from NLU channel")
    for ep in fetch_episodes():
        fetch_episode_transcript(ep.number, videos)


if __name__ == "__main__":
    main()
