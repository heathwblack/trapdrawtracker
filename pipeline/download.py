"""Download MP3s for the episodes returned by fetch_feed."""
from __future__ import annotations

from pathlib import Path

import requests

from pipeline.config import AUDIO_DIR
from pipeline.fetch_feed import Episode, fetch_episodes


def audio_path(number: int) -> Path:
    return AUDIO_DIR / f"{number}.mp3"


def download_episode(ep: Episode) -> Path:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out = audio_path(ep.number)
    if out.exists() and out.stat().st_size > 0:
        print(f"  skip  {ep.number}  (already downloaded)")
        return out
    print(f"  get   {ep.number}  {ep.mp3_url}")
    with requests.get(ep.mp3_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        tmp = out.with_suffix(".mp3.part")
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
        tmp.rename(out)
    return out


def main() -> None:
    eps = fetch_episodes()
    for ep in eps:
        download_episode(ep)


if __name__ == "__main__":
    main()
