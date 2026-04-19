# Trap Draw Tracker

A tracker for topics the Trap Draw hosts "monitor" on **Chop Session** episodes — the substantive stories they dig into each week, with their POV and a status line for each one. Scoped to 2026 episodes.

**Published site:** https://heathwblack.github.io/trapdrawtracker/

## How it works

```
RSS feed ──▶ filter ──▶ YouTube captions ──▶ extract ──▶ JSON ──▶ static site
         (Chop 2026)   (yt-dlp auto-subs)   (Claude)
```

1. `fetch_feed.py` pulls the [Trap Draw RSS](https://feeds.megaphone.fm/trapdraw) and keeps episodes whose title matches `^\d+: Chop Session` published in 2026.
2. `fetch_captions.py` uses `yt-dlp` to match each episode to its video on the [NLU YouTube channel](https://www.youtube.com/@NoLayingUpPodcast) and downloads English auto-captions in json3 format, converting them to a segment-level transcript at `data/transcripts/{ep}.json`.
3. `extract.py` sends each transcript to Claude via tool-use; Claude returns the monitoring items (title, topic, category, timestamp, POV summary, status, quote).
4. `docs/items.json` is the served payload; the static site in `docs/` fetches and renders it.

Every stage is idempotent — rerun and it skips finished work.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY

brew install yt-dlp   # enumerates videos and pulls captions
```

## Run

```bash
./scripts/run_all.sh           # full pipeline end-to-end
# or piecemeal:
python3 -m pipeline.fetch_feed       # list 2026 Chop Sessions
python3 -m pipeline.fetch_captions   # pull YouTube auto-captions
python3 -m pipeline.extract          # Claude → items.json
```

View the site locally:
```bash
python3 -m http.server 8000 --directory docs
open http://localhost:8000
```

## Deploy

GitHub Pages → Settings → Pages → Source: `main` branch, `/docs` folder. Push and it's live.

## Layout

```
pipeline/      # three pipeline stages + config
data/          # committed transcripts
docs/          # static site + items.json (served by GH Pages)
scripts/       # run_all.sh
```

## Notes

- YouTube auto-captions are lower quality than a dedicated transcription pass (no punctuation, occasional word errors) but Claude handles messy text fine for topic extraction. If quality becomes a problem, swap `fetch_captions.py` for a whisper.cpp-backed transcriber — `extract.py` is agnostic to how transcripts are produced.
- Costs: one Claude Opus 4.7 call per episode. With ~8 episodes and ~15–20k-token transcripts, all 2026 episodes run ~$1–3.
